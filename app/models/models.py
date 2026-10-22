from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash:Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
class Document(Base):
    __tablename__="documents"

    id:Mapped[int]= mapped_column(primary_key= True)
    tenant_id: Mapped[int]= mapped_column(ForeignKey("tenants.id"),nullable= False)
    title:Mapped[str] = mapped_column(
        String(255),
        nullable= False,
    )
    created_at: Mapped[datetime]= mapped_column(
        DateTime,
        default= datetime.utcnow,
        nullable= False
    )
class Chunk (Base):
    __tablename__="chunks"

    id: Mapped[int] = mapped_column(primary_key = True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"),nullable=False)
    document_id:Mapped[int] = mapped_column(ForeignKey("documents.id"),nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    chunk_index: Mapped[int]= mapped_column(nullable=False)
    allowed_roles: Mapped[list[str]]= mapped_column(
        ARRAY(String),
        nullable= False,
        default= list,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[int] = mapped_column(primary_key= True)
    tenant_id :Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
        index= True,
    )
    user_id: Mapped[int|None] = mapped_column(
        ForeignKey("users.id"),
        nullable= True
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable= False
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable = False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    chunks_retrieved: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable = False
        )
