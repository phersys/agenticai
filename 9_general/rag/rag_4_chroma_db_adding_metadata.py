import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma with persistence
client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

# Hugging Face embedding function
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create / load collection with embedding function
collection = client.get_or_create_collection(
    name="my_collection_hf_with_metadata",
    embedding_function=embedding_fn
)

# Knowledge base with metadata
knowledge_base = {
    "shipping_time": {
        "text": "Our standard shipping time is 3-5 business days.",
        "metadata": {"category": "shipping", "priority": "high"}
    },
    "return_policy": {
        "text": "You can return any product within 30 days of delivery.",
        "metadata": {"category": "returns", "priority": "medium"}
    },
    "warranty": {
        "text": "All products come with a one-year warranty covering manufacturing defects.",
        "metadata": {"category": "warranty", "priority": "medium"}
    },
    "payment_methods": {
        "text": "We accept credit cards, debit cards, and PayPal.",
        "metadata": {"category": "payment", "priority": "low"}
    },
    "customer_support": {
        "text": "You can reach our support team 24/7 via email or chat.",
        "metadata": {"category": "support", "priority": "high"}
    }
}

# Add data with metadata
collection.add(
    documents=[item["text"] for item in knowledge_base.values()],
    ids=list(knowledge_base.keys()),
    metadatas=[item["metadata"] for item in knowledge_base.values()]
)

# Query ChromaDB using HF embeddings
results = collection.query(
    query_texts=["delivery lag"],
    n_results=2
)

print(results)
