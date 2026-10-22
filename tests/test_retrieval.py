from app.database import SessionLocal
from app.retrieval.service import search_chunks


def test_company_admin_access():
    db = SessionLocal()
    try:
        chunks = search_chunks(
            db=db,
            tenant_id=1,
            role="admin",
        )

        assert len(chunks) > 0
        assert all(chunk.tenant_id == 1 for chunk in chunks)
    finally:
        db.close()


def test_company_a_finance_access():
    db = SessionLocal()
    try:
        chunks = search_chunks(
            db=db,
            tenant_id=1,
            role="finance",
        )

        assert len(chunks) > 0
        assert all(chunk.tenant_id == 1 for chunk in chunks)
        assert all("finance" in chunk.allowed_roles for chunk in chunks)
    finally:
        db.close()


def test_company_b_admin_access():
    db = SessionLocal()
    try:
        chunks = search_chunks(
            db=db,
            tenant_id=2,
            role="admin",
        )

        assert len(chunks) > 0
        assert all(chunk.tenant_id == 2 for chunk in chunks)
    finally:
        db.close()


def test_tenant_isolation():
    db = SessionLocal()
    try:
        company_a_chunks = search_chunks(
            db=db,
            tenant_id=1,
            role="admin",
        )

        company_b_chunks = search_chunks(
            db=db,
            tenant_id=2,
            role="admin",
        )

        assert all(chunk.tenant_id == 1 for chunk in company_a_chunks)
        assert all(chunk.tenant_id == 2 for chunk in company_b_chunks)
    finally:
        db.close()
