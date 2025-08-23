from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "agent"

class UserCreate(UserBase):
    password: str
    company_id: int

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Company schemas
class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# Project schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    company_id: int

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class Project(ProjectBase):
    id: int
    company_id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# Call schemas
class CallBase(BaseModel):
    filename: str
    agent_name: Optional[str] = None
    customer_name: Optional[str] = None

class CallCreate(CallBase):
    project_id: int
    s3_key: str

class CallUpdate(BaseModel):
    status: Optional[str] = None
    transcription_job_name: Optional[str] = None
    s3_output_key: Optional[str] = None
    agent_name: Optional[str] = None
    customer_name: Optional[str] = None
    call_duration: Optional[float] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class Call(CallBase):
    id: int
    project_id: int
    s3_key: str
    s3_output_key: Optional[str] = None
    transcription_job_name: Optional[str] = None
    status: str
    call_duration: Optional[float] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

# QA Report schemas
class QAReportBase(BaseModel):
    transcript: Optional[str] = None
    corrected_transcript: Optional[str] = None
    agent_summary: Optional[str] = None
    qa_scores: Optional[Dict[str, Any]] = None
    qa_feedback: Optional[str] = None
    overall_score: Optional[float] = None
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    model_used: Optional[str] = None
    processing_time_seconds: Optional[float] = None

class QAReportCreate(QAReportBase):
    call_id: int

class QAReport(QAReportBase):
    id: int
    call_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Upload schemas
class UploadRequest(BaseModel):
    filename: str
    content_type: str

class UploadResponse(BaseModel):
    upload_url: str
    s3_key: str
    call_id: int

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Dashboard schemas
class DashboardStats(BaseModel):
    total_calls: int
    processed_calls: int
    pending_calls: int
    failed_calls: int
    average_score: Optional[float] = None
    total_processing_time: Optional[float] = None

class AgentPerformance(BaseModel):
    agent_name: str
    total_calls: int
    average_score: Optional[float] = None
    recent_calls: int = 0
