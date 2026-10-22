from sqlalchemy import select

from app.database import SessionLocal
from app.models.models import Tenant, User, Document, Chunk
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
import os

DEV_PASSWORDS = {
    "alice@company-a.com": os.getenv("SEED_ALICE_PASSWORD"),
    "ahme@company-a.com": os.getenv("SEED_AHMED_PASSWORD"),
    "salim@company-a.com": os.getenv("SEED_SALIM_PASSWORD"),
    "david@company-b.com": os.getenv("SEED_DAVID_PASSWORD"),
}
missing_passwords = [
    email
    for email, password in DEV_PASSWORDS.items()
    if not password
]

if missing_passwords:
    raise RuntimeError(
        "Missing seed passwords in environment variables for: "
        + ", ".join(missing_passwords)
    )
def seed():
    db= SessionLocal()

    try:
        tenant_a= db.scalar(
            select(Tenant).where(Tenant.name == "Company A")
        )
        if tenant_a is None:
            tenant_a = Tenant(name="Company A")
            db.add(tenant_a)
        tenant_b= db.scalar(
            select(Tenant).where(Tenant.name == "Company B")
        )
        if tenant_b is None:
            tenant_b=Tenant(name="Company B")
            db.add(tenant_b)

        db.flush()
        users_data = [
            ("alice@company-a.com","admin",tenant_a.id),
            ("ahme@company-a.com","finance",tenant_a.id),
            ("salim@company-a.com","employee",tenant_a.id),
            ("david@company-b.com","admin",tenant_b.id),
        ]
        for email,role,tenant_id in users_data:
            user = db.scalar(
                select(User).where(User.email == email)
            )
            if user is None:
                user = User(email=email,role=role,tenant_id=tenant_id,password_hash=password_hash.hash(DEV_PASSWORDS[email]))
                db.add(user)
            elif not user.password_hash:
                user.password_hash= password_hash.hash(DEV_PASSWORDS[email])
            db.flush()

        finance_report = db.scalar(
            select(Document).where(
                Document.title== "Finance Report",
                Document.tenant_id==tenant_a.id,
            )

        )
        if finance_report is None:
            finance_report=Document(
                tenant_id=tenant_a.id,
                title="Finance Report",
            )
            db.add(finance_report)
        employee_handbook = db.scalar(
            select(Document).where(
                Document.title=="Employee Handbook",
                Document.tenant_id==tenant_a.id,
            )
        )

        if employee_handbook is None:
            employee_handbook = Document(
                tenant_id=tenant_a.id,
                title="Employee Handbook"
            )
            db.add(employee_handbook)

        internal_report= db.scalar(
            select(Document).where(
                Document.title=="Internal Report",
                Document.tenant_id== tenant_b.id
            )
        )
        if internal_report is None:
            internal_report = Document(
                tenant_id= tenant_b.id,
                title = "Internal Report"
            )
            db.add(internal_report)

        db.flush()
        chunks_data = [
            (
                finance_report.id,
                tenant_a.id,
                "Company A quartely revenue Increased by 15 percent",
                0,
                ["admin", "finance"],
            ),
            (
                finance_report.id,
                tenant_a.id,
                "Company A financial forecast for the next quarter",
                1,
                ["admin"]
            ),
            (
                employee_handbook.id,
                tenant_a.id,
                "Employees must follow the company security policy",
                0,
                ["admin","employee"]
            ),
            (
                internal_report.id,
                tenant_b.id,
                "Company B internal strategic planing document",
                0,
                ["admin"]
            )

        ]
        for document_id, tenant_id, content,chunk_index,allowed_roles in chunks_data:
            existing_chunk = db.scalar(
                select(Chunk).where(
                    Chunk.document_id == document_id,
                    Chunk.chunk_index == chunk_index
                )
            )
            if existing_chunk is None:
                db.add(
                    Chunk(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        content=content,
                        chunk_index=chunk_index,
                        allowed_roles=allowed_roles,
                    )
                )

        db.commit()
        print("Seed completed successfully")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
