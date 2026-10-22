from app.database import SessionLocal
from app.embeddings import create_embedding
from app.models.models import Chunk

def embed_all_chunks():
    db=SessionLocal()

    try:
        chunks = db.query(Chunk).all()

        for chunk in chunks:
            print(f"Embedding chunk {chunk.id}...")

            chunk.embedding= create_embedding(chunk.content)
        db.commit()
        print(f"Embedded{len(chunks)} chunks succeffully")
    finally:
        db.close()

if __name__=='__main__':
    embed_all_chunks()