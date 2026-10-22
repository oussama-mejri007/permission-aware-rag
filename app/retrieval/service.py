from sqlalchemy import any_, select

from app.models.models import Chunk


def search_chunks(
    db,
    tenant_id: int,
    role: str,
):
    query = select(Chunk).where(
        Chunk.tenant_id == tenant_id,
        any_(Chunk.allowed_roles) == role,
    )

    return db.scalars(query).all()

def search_similar_chunks(db,query_embedding: list[float], limit: int=5):
    query=(select(Chunk).order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(limit))
    return db.scalars(query).all()

def search_authorized_chunks(db,query_embedding: list[float],tenant_id: int,role: str,limit: int = 5):
    query = (
        select(Chunk)
        .where(
            Chunk.tenant_id == tenant_id,
            any_(Chunk.allowed_roles) == role,
        )
        .order_by(
            Chunk.embedding.cosine_distance(query_embedding)
        )
        .limit(limit)
    )

    return db.scalars(query).all()
