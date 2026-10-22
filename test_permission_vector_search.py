from app.database import SessionLocal
from app.embeddings import create_embedding
from app.retrieval.service import search_authorized_chunks


def run_test(tenant_id, role, question):
    db = SessionLocal()

    try:
        embedding = create_embedding(question)

        chunks = search_authorized_chunks(
            db=db,
            query_embedding=embedding,
            tenant_id=tenant_id,
            role=role,
            limit=5,
        )

        print(f"\nTenant={tenant_id}, role={role}")
        for chunk in chunks:
            print(f"  Chunk {chunk.id}: {chunk.content}")

        assert all(c.tenant_id == tenant_id for c in chunks)
        assert all(role in c.allowed_roles for c in chunks)

        return chunks

    finally:
        db.close()


if __name__ == "__main__":
    finance = run_test(1, "finance", "Company A revenue")
    employee = run_test(1, "employee", "Company A security policy")
    company_b = run_test(2, "admin", "Company B strategic plan")

    assert len(finance) == 1
    assert len(employee) == 1
    assert len(company_b) == 1

    assert all(c.tenant_id == 1 for c in finance)
    assert all(c.tenant_id == 1 for c in employee)
    assert all(c.tenant_id == 2 for c in company_b)

    print("\nAll permission tests passed!")
