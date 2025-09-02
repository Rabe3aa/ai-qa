from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import uuid
import boto3
import logging
from datetime import datetime
from fastapi.responses import StreamingResponse
import io
import csv
from ..database import get_db
from ..models import Call, QAReport, User, Project
from ..schemas import Call as CallSchema, QAReport as QAReportSchema, UploadRequest, UploadResponse
from ..auth import get_current_active_user, require_company_manager
from ..qa_service import EnhancedQAService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization to avoid startup-time side effects
def get_s3_client():
    return boto3.client('s3', region_name=settings.aws_region)

def get_qa_service():
    return EnhancedQAService()

@router.post("/upload-url", response_model=UploadResponse)
async def create_upload_url(
    request: UploadRequest,
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create presigned URL for S3 upload and call record"""
    try:
        # Generate unique S3 key
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{project_id}/{file_id}_{request.filename}"
        
        # Create presigned URL
        upload_url = get_s3_client().generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.aws_s3_bucket_input,
                'Key': s3_key,
                'ContentType': request.content_type
            },
            ExpiresIn=3600
        )
        
        # Create call record
        call = Call(
            project_id=project_id,
            filename=request.filename,
            s3_key=s3_key,
            status="uploaded"
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        
        return UploadResponse(
            upload_url=upload_url,
            s3_key=s3_key,
            call_id=call.id
        )
        
    except Exception as e:
        logger.error(f"Failed to create upload URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to create upload URL")

@router.post("/{call_id}/analyze")
async def analyze_call(
    call_id: int,
    background_tasks: BackgroundTasks,
    model: str = "gpt-4o",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start call analysis"""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Update status
    call.status = "processing"
    db.commit()
    
    # Start background analysis
    background_tasks.add_task(process_call_analysis, call_id, model)
    
    return {"message": "Analysis started", "call_id": call_id}

def process_call_analysis(call_id: int, model: str = "gpt-4o"):
    """Background task to process call analysis"""
    db = next(get_db())
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return
        
        # Generate job name
        job_name = f"qa-call-{call_id}-{int(datetime.now().timestamp())}"
        
        # Start transcription
        qa_service = get_qa_service()
        s3_output_key = qa_service.start_transcription(call.s3_key, job_name)
        call.transcription_job_name = job_name
        call.s3_output_key = s3_output_key
        db.commit()
        
        # Wait for transcription
        transcript = qa_service.get_transcription(job_name)
        if not transcript:
            call.status = "failed"
            call.error_message = "Transcription failed"
            db.commit()
            return
        
        # Correct transcript
        corrected_transcript = qa_service.correct_transcript(transcript)
        
        # Generate QA feedback
        qa_result = qa_service.generate_feedback(corrected_transcript, model)
        
        # Create QA report
        qa_report = QAReport(
            call_id=call_id,
            transcript=transcript,
            corrected_transcript=corrected_transcript,
            agent_summary=qa_result.get("agent_summary", ""),
            qa_scores=qa_result.get("qa_scores", {}),
            qa_feedback=qa_result.get("qa_feedback", ""),
            overall_score=qa_result.get("overall_score", 0),
            positive_count=qa_result.get("positive_count", 0),
            negative_count=qa_result.get("negative_count", 0),
            neutral_count=qa_result.get("neutral_count", 0),
            model_used=qa_result.get("model_used", model),
            processing_time_seconds=qa_result.get("processing_time_seconds", 0)
        )
        
        db.add(qa_report)
        call.status = "completed"
        call.processed_at = datetime.now()
        db.commit()
        
        logger.info(f"Call {call_id} analysis completed")
        
    except Exception as e:
        logger.error(f"Call analysis failed for {call_id}: {e}")
        call = db.query(Call).filter(Call.id == call_id).first()
        if call:
            call.status = "failed"
            call.error_message = str(e)
            db.commit()
    finally:
        db.close()

@router.get("/{call_id}", response_model=CallSchema)
async def get_call(
    call_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get call details"""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call

@router.get("/{call_id}/report", response_model=QAReportSchema)
async def get_call_report(
    call_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get QA report for call"""
    report = db.query(QAReport).filter(QAReport.call_id == call_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/", response_model=List[CallSchema])
async def list_calls(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agent: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List calls with optional filtering"""
    query = db.query(Call)
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    if project_id:
        query = query.filter(Call.project_id == project_id)
    if status:
        query = query.filter(Call.status == status)
    if start_date:
        query = query.filter(Call.uploaded_at >= start_date)
    if end_date:
        query = query.filter(Call.uploaded_at <= end_date)
    if agent:
        query = query.filter(Call.agent_name.ilike(f"%{agent}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Call.filename.ilike(like),
                Call.agent_name.ilike(like),
                Call.customer_name.ilike(like)
            )
        )
    
    return query.order_by(Call.uploaded_at.desc()).limit(limit).all()

@router.get("/export")
async def export_calls(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agent: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export calls as CSV with current filters"""
    query = db.query(Call)
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    if project_id:
        query = query.filter(Call.project_id == project_id)
    if status:
        query = query.filter(Call.status == status)
    if start_date:
        query = query.filter(Call.uploaded_at >= start_date)
    if end_date:
        query = query.filter(Call.uploaded_at <= end_date)
    if agent:
        query = query.filter(Call.agent_name.ilike(f"%{agent}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Call.filename.ilike(like),
                Call.agent_name.ilike(like),
                Call.customer_name.ilike(like)
            )
        )

    rows = query.order_by(Call.uploaded_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "project_id", "filename", "agent_name", "customer_name", "status",
        "uploaded_at", "processed_at", "call_duration", "error_message"
    ])
    for c in rows:
        writer.writerow([
            c.id,
            c.project_id,
            c.filename,
            c.agent_name or "",
            c.customer_name or "",
            c.status,
            c.uploaded_at.isoformat() if c.uploaded_at else "",
            c.processed_at.isoformat() if c.processed_at else "",
            c.call_duration if c.call_duration is not None else "",
            c.error_message or "",
        ])

    buffer.seek(0)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f"attachment; filename=calls_{ts}.csv"
    }
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)

@router.post("/process-pending")
async def process_pending_calls(
    background_tasks: BackgroundTasks,
    project_id: Optional[int] = None,
    limit: int = 20,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db)
):
    """Batch process pending calls"""
    query = db.query(Call).filter(Call.status == "uploaded")
    
    if project_id:
        query = query.filter(Call.project_id == project_id)
    
    if current_user.role != "admin":
        # Filter by company
        from ..models import Project
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    pending_calls = query.limit(limit).all()
    
    for call in pending_calls:
        background_tasks.add_task(process_call_analysis, call.id)
    
    return {
        "message": "Pending call processing started",
        "calls_queued": len(pending_calls)
    }
