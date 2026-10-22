from app.database import SessionLocal
from app.embeddings  import create_embedding
from app.llm import generate_answer
from app.models.models import AuditLog
from app.retrieval.service  import search_authorized_chunks

def ask_question(question:str,tenant_id: int,role: str,user_id:int|None= None)-> str:
    db = SessionLocal()
    try:
        query_embedding = create_embedding(question)

        chunks= search_authorized_chunks(db=db,query_embedding=query_embedding,tenant_id=tenant_id,role=role,limit = 5)

        audit_status="success" if chunks else"no_authorized_chunks"
        db.add(AuditLog(tenant_id=tenant_id,user_id=user_id,role=role,event_type="rag_query",status=audit_status,chunks_retrieved=len(chunks)))
        db.commit()

        if not chunks:return "i don't have enough authorized information to answer"

        context = "\n\n".join(chunk.content for chunk in chunks)

        return generate_answer(question,context)
    finally:
        db.close()
