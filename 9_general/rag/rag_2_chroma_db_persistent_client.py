# Use a persistent ChromaDB
# Add our knowledge base to the collection
# Query the collection using semantic search
import chromadb

client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

collection = client.get_or_create_collection(name="my_collection")

knowledge_base = {
    "shipping_time": "Our standard shipping time is 3-5 business days.",
    "return_policy": "You can return any product within 30 days of delivery.",
    "warranty": "All products come with a one-year warranty covering manufacturing defects.",
    "payment_methods": "We accept credit cards, debit cards, and PayPal.",
    "customer_support": "You can reach our support team 24/7 via email or chat."
}

collection.add(
    documents=list(knowledge_base.values()),
    ids=list(knowledge_base.keys())
)

# Query is always on the values (documents), not keys
results = collection.query(
    query_texts=["i want to use cash"], # Chroma will embed this for you
    n_results=1 # how many results to return
)
print(results)
