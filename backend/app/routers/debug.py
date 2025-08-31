from fastapi import APIRouter
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from .. import database
from ..database import SessionLocal, Base
from ..models import Company, User, Project, Call, QAReport
from ..seeder import seed_demo_data

router = APIRouter()

@router.get("/db")
async def db_health():
    """Return DB health: dialect, tables, and basic counts. No auth; remove after debugging."""
    info = {"ok": True, "errors": []}
    try:
        engine = database.engine
        insp = inspect(engine)
        existing = sorted(insp.get_table_names())
        expected = sorted(list(Base.metadata.tables.keys()))
        info["dialect"] = engine.name
        # Avoid leaking credentials. Only expose basename/path for sqlite
        db_url = database.database_url or ""
        if engine.name == "sqlite":
            # sqlite:///./qa_system.db -> ./qa_system.db
            try:
                from sqlalchemy.engine.url import make_url
                info["sqlite_path"] = make_url(db_url).database
            except Exception:
                info["sqlite_path"] = db_url
        info["tables"] = {"expected": expected, "existing": existing}
        counts = {}
        db: Session = SessionLocal()
        try:
            # Count per table (ignore if table missing)
            if "companies" in existing:
                counts["companies"] = db.query(Company).count()
            if "users" in existing:
                counts["users"] = db.query(User).count()
            if "projects" in existing:
                counts["projects"] = db.query(Project).count()
            if "calls" in existing:
                counts["calls"] = db.query(Call).count()
            if "qa_reports" in existing:
                counts["qa_reports"] = db.query(QAReport).count()
        finally:
            db.close()
        info["counts"] = counts
    except Exception as e:
        info["ok"] = False
        info["errors"].append(str(e))
    return info

@router.post("/seed-demo")
async def seed_demo():
    """Force re-seed demo data (admin, manager, agent, and a demo project). No auth; remove after debugging."""
    try:
        seed_demo_data()
        return {"ok": True, "message": "Demo data seeded (if not already present)."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
