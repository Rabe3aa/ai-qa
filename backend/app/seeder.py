from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Company, User, Project
from .auth import get_password_hash
import logging

logger = logging.getLogger(__name__)

def seed_demo_data():
    """Seed demo data for testing"""
    db = SessionLocal()
    try:
        # Check if demo data already exists
        if db.query(Company).filter(Company.name == "Demo Company").first():
            logger.info("Demo data already exists, skipping seeding")
            return
        
        # Create demo company
        demo_company = Company(name="Demo Company")
        db.add(demo_company)
        db.commit()
        db.refresh(demo_company)
        
        # Create demo users
        users = [
            {
                "email": "admin@example.com",
                "password": "admin123",
                "full_name": "System Admin",
                "role": "admin",
                "company_id": demo_company.id
            },
            {
                "email": "manager@example.com", 
                "password": "manager123",
                "full_name": "QA Manager",
                "role": "company_manager",
                "company_id": demo_company.id
            },
            {
                "email": "agent@example.com",
                "password": "agent123", 
                "full_name": "Call Agent",
                "role": "agent",
                "company_id": demo_company.id
            }
        ]
        
        for user_data in users:
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                company_id=user_data["company_id"]
            )
            db.add(user)
        
        # Create demo project
        demo_project = Project(
            name="Customer Service QA",
            description="Quality assurance for customer service calls",
            company_id=demo_company.id
        )
        db.add(demo_project)
        
        db.commit()
        logger.info("Demo data seeded successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")
        db.rollback()
    finally:
        db.close()
