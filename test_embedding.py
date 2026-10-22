from app.embeddings import create_embedding


embedding = create_embedding(
    "Company A quarterly revenue increased by 15 percent"
)

print("Dimensions:", len(embedding))
print("First 5 values:", embedding[:5])
