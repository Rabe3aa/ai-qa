from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from .database import SessionLocal
from .models import Call
from .routers.calls import process_call_analysis

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def process_pending_calls_job():
    """Background job to process pending calls"""
    db = SessionLocal()
    try:
        # Use row-level locking to safely claim calls
        if db.bind.dialect.name == 'postgresql':
            # PostgreSQL supports FOR UPDATE SKIP LOCKED
            pending_calls = db.execute(
                text("""
                    SELECT id FROM calls 
                    WHERE status = 'uploaded' 
                    ORDER BY uploaded_at ASC 
                    LIMIT 10 
                    FOR UPDATE SKIP LOCKED
                """)
            ).fetchall()
            
            call_ids = [row[0] for row in pending_calls]
            
            # Update status to processing
            if call_ids:
                db.execute(
                    text("UPDATE calls SET status = 'processing' WHERE id = ANY(:ids)"),
                    {"ids": call_ids}
                )
                db.commit()
        else:
            # Fallback for other databases
            pending_calls = db.query(Call).filter(
                Call.status == "uploaded"
            ).order_by(Call.uploaded_at.asc()).limit(10).all()
            
            call_ids = []
            for call in pending_calls:
                call.status = "processing"
                call_ids.append(call.id)
            
            db.commit()
        
        # Process each call
        for call_id in call_ids:
            try:
                process_call_analysis(call_id)
                logger.info(f"Processed call {call_id}")
            except Exception as e:
                logger.error(f"Failed to process call {call_id}: {e}")
                # Reset status on failure
                call = db.query(Call).filter(Call.id == call_id).first()
                if call:
                    call.status = "failed"
                    call.error_message = str(e)
                    db.commit()
        
        if call_ids:
            logger.info(f"Processed {len(call_ids)} pending calls")
            
    except Exception as e:
        logger.error(f"Scheduler job failed: {e}")
    finally:
        db.close()

def start_scheduler():
    """Start the background scheduler"""
    if not scheduler.running:
        # Process pending calls every hour
        scheduler.add_job(
            func=process_pending_calls_job,
            trigger=IntervalTrigger(hours=1),
            id='process_pending_calls',
            name='Process pending calls',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started")

def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
