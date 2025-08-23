from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Project, User
from ..schemas import Project as ProjectSchema, ProjectCreate, ProjectUpdate
from ..auth import get_current_active_user, require_company_manager

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectSchema)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    # Verify user can create project for this company
    if current_user.role != "admin" and current_user.company_id != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db_project = Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectSchema])
async def list_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List projects accessible to the user"""
    query = db.query(Project)
    
    if current_user.role == "company_manager":
        query = query.filter(Project.company_id == current_user.company_id)
    elif current_user.role == "agent":
        # Agents can see projects from their company
        query = query.filter(Project.company_id == current_user.company_id)
    
    return query.filter(Project.is_active == True).all()

@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify access
    if current_user.role != "admin" and current_user.company_id != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return project

@router.put("/{project_id}", response_model=ProjectSchema)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db)
):
    """Update project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify access
    if current_user.role != "admin" and current_user.company_id != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    for field, value in project_update.dict(exclude_unset=True).items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project
