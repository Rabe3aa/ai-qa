from fastapi import APIRouter, Depends
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from .. import database
from ..database import SessionLocal, Base
from ..models import Company, User, Project, Call, QAReport
from ..seeder import seed_demo_data
from jose import jwt, JWTError
from ..auth import SECRET_KEY, ALGORITHM, oauth2_scheme, SECONDARY_SECRET_KEY
import hashlib

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

@router.post("/create-tables")
async def create_tables():
    """Create all ORM tables now (production DB). No auth; remove after debugging."""
    try:
        Base.metadata.create_all(bind=database.engine)
        # Re-check existing tables
        insp = inspect(database.engine)
        existing = sorted(insp.get_table_names())
        return {"ok": True, "message": "Tables created", "existing": existing}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/jwt/fingerprint")
async def jwt_fingerprint():
    """Return a non-secret fingerprint of the JWT secret to detect instance mismatch. No auth; remove after debugging."""
    try:
        key = SECRET_KEY or ""
        fp = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        return {"ok": True, "algorithm": ALGORITHM, "secret_sha256_prefix": fp, "length": len(key)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/jwt/decode")
async def jwt_decode(token: str = Depends(oauth2_scheme)):
    """Attempt to decode the provided Bearer token with primary/secondary keys and return minimal payload info. Remove after debugging."""
    last_error = None
    for which, key in [("primary", SECRET_KEY), ("secondary", SECONDARY_SECRET_KEY)]:
        if not key:
            continue
        try:
            payload = jwt.decode(token, key, algorithms=[ALGORITHM])
            return {"ok": True, "using": which, "sub": payload.get("sub"), "exp": payload.get("exp")}
        except JWTError as e:
            last_error = e
            continue
    return {"ok": False, "error": f"Signature verification failed with both keys: {last_error}"}
