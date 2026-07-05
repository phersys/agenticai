import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma with persistence
client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

# Hugging Face embedding function
# These are higher quality embeddings
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create / load collection with embedding function
collection = client.get_or_create_collection(
    name="my_collection_hf",
    embedding_function=embedding_fn
)

# Knowledge base
knowledge_base = {
    "shipping_time": "Our standard shipping time is 3-5 business days.",
    "return_policy": "You can return any product within 30 days of delivery.",
    "warranty": "All products come with a one-year warranty covering manufacturing defects.",
    "payment_methods": "We accept credit cards, debit cards, and PayPal.",
    "customer_support": "You can reach our support team 24/7 via email or chat."
}

# Add data
collection.add(
    documents=list(knowledge_base.values()),
    ids=list(knowledge_base.keys())
)

# Query ChromaDB using HF embeddings
results = collection.query(
    query_texts=["delivery lag"],
    n_results=2
)

print(results)
