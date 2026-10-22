from app.database import SessionLocal
from app.embeddings import create_embedding
from app.retrieval.service import search_authorized_chunks


db = SessionLocal()

try:
    question = "What was Company A revenue?"
    query_embedding = create_embedding(question)

    chunks = search_authorized_chunks(
        db=db,
        query_embedding=query_embedding,
        tenant_id=1,
        role="finance",
        limit=5,
    )

    for chunk in chunks:
        print(f"Chunk {chunk.id}: {chunk.content}")

finally:
    db.close()
