from app.database import SessionLocal
from app.embeddings import create_embedding
from app.models.models import AuditLog
from app.retrieval.service import search_authorized_chunks

def test_no_cross_tenant_data_leakage():
    db= SessionLocal()
    try:
        chunks=search_authorized_chunks(db=db,query_embedding=create_embedding("Company B internal strategic plan"),tenant_id=1,role="admin",limit=5)
        assert all(chunk.tenant_id == 1 for chunk in chunks)
    finally:
        db.close()

def test_role_based_access():
    db=SessionLocal()
    try:
        chunks=search_authorized_chunks(db=db,query_embedding=create_embedding("Company A financial forecast"),tenant_id=1,role="employee",limit=5)
        assert all("employee" in chunk.allowed_roles for chunk in chunks)
    finally:
        db.close()

def test_audit_log_record_authorized_search():
    db = SessionLocal()
    try:
        log= (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id==2,
                AuditLog.role == "employee",
                AuditLog.status== "no authorized chunks",
                AuditLog.chunks_retrieved ==0,
            )
            .first
        )
        assert log is not None
    finally:
        db.close()
