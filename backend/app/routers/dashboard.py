from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from datetime import datetime
import io
import csv
from ..database import get_db
from ..models import Call, QAReport, User, Project
from ..schemas import DashboardStats, AgentPerformance
from ..auth import get_current_active_user

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    project_id: int = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    query = db.query(Call)
    
    # Filter by company for non-admin users
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    if project_id:
        query = query.filter(Call.project_id == project_id)
    if start_date:
        query = query.filter(Call.uploaded_at >= start_date)
    if end_date:
        query = query.filter(Call.uploaded_at <= end_date)
    
    total_calls = query.count()
    processed_calls = query.filter(Call.status == "completed").count()
    pending_calls = query.filter(Call.status.in_(["uploaded", "processing"])).count()
    failed_calls = query.filter(Call.status == "failed").count()
    
    # Get average score
    filtered_call_ids = [c.id for c in query.all()]
    avg_score = None
    total_time = None
    if filtered_call_ids:
        avg_score = db.query(func.avg(QAReport.overall_score)).join(Call).filter(
            Call.id.in_(filtered_call_ids)
        ).scalar()
        # Get total processing time
        total_time = db.query(func.sum(QAReport.processing_time_seconds)).join(Call).filter(
            Call.id.in_(filtered_call_ids)
        ).scalar()
    
    return DashboardStats(
        total_calls=total_calls,
        processed_calls=processed_calls,
        pending_calls=pending_calls,
        failed_calls=failed_calls,
        average_score=avg_score,
        total_processing_time=total_time
    )

@router.get("/agent-performance", response_model=List[AgentPerformance])
async def get_agent_performance(
    project_id: int = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agent: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get agent performance metrics"""
    query = db.query(
        Call.agent_name,
        func.count(Call.id).label('total_calls'),
        func.avg(QAReport.overall_score).label('average_score'),
        func.sum(case((Call.status == 'completed', 1), else_=0)).label('recent_calls')
    ).outerjoin(QAReport)
    
    # Filter by company for non-admin users
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    if project_id:
        query = query.filter(Call.project_id == project_id)
    if start_date:
        query = query.filter(Call.uploaded_at >= start_date)
    if end_date:
        query = query.filter(Call.uploaded_at <= end_date)
    if agent:
        query = query.filter(Call.agent_name.ilike(f"%{agent}%"))

    results = query.filter(Call.agent_name.isnot(None)).group_by(Call.agent_name).all()
    
    return [
        AgentPerformance(
            agent_name=result.agent_name,
            total_calls=result.total_calls,
            average_score=result.average_score,
            recent_calls=result.recent_calls or 0
        )
        for result in results
    ]

@router.get("/agent-performance/export")
async def export_agent_performance(
    project_id: int = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agent: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export agent performance as CSV"""
    query = db.query(
        Call.agent_name,
        func.count(Call.id).label('total_calls'),
        func.avg(QAReport.overall_score).label('average_score'),
        func.sum(case((Call.status == 'completed', 1), else_=0)).label('recent_calls')
    ).outerjoin(QAReport)

    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)

    if project_id:
        query = query.filter(Call.project_id == project_id)
    if start_date:
        query = query.filter(Call.uploaded_at >= start_date)
    if end_date:
        query = query.filter(Call.uploaded_at <= end_date)
    if agent:
        query = query.filter(Call.agent_name.ilike(f"%{agent}%"))

    results = query.filter(Call.agent_name.isnot(None)).group_by(Call.agent_name).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["agent_name", "total_calls", "average_score", "recent_calls"])
    for r in results:
        writer.writerow([
            r.agent_name,
            r.total_calls,
            f"{r.average_score:.2f}" if r.average_score is not None else "",
            r.recent_calls or 0
        ])
    buffer.seek(0)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    headers = {"Content-Disposition": f"attachment; filename=agent_performance_{ts}.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
