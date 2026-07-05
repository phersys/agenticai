import chromadb
from chromadb.utils import embedding_functions
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
import os

# --------------------------------
# CONFIGURE OLLAMA ENDPOINT
# --------------------------------
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

# --------------------------------
# INITIALIZE CHROMADB
# --------------------------------
client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

# Hugging Face embedding function
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create / load collection with embedding function
collection = client.get_or_create_collection(
    name="my_collection_hf_with_metadata_search",
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

# Add data with metadata (only if collection is empty)
if collection.count() == 0:
    collection.add(
        documents=[item["text"] for item in knowledge_base.values()],
        ids=list(knowledge_base.keys()),
        metadatas=[item["metadata"] for item in knowledge_base.values()]
    )
    print("Knowledge base loaded into ChromaDB")
else:
    print(f"ChromaDB already contains {collection.count()} documents")

# --------------------------------
# INITIALIZE LANGCHAIN WITH OLLAMA
# --------------------------------
model = Ollama(
    model="llama3.2:latest",
    base_url="http://localhost:11434"
)

# --------------------------------
# CREATE RAG PROMPT TEMPLATE
# --------------------------------
rag_template = """You are a helpful customer support assistant. 
Use the following context from our knowledge base to answer the user's question.
If the answer cannot be found in the context, say "I don't have that information in our knowledge base."

Context:
{context}

User Question: {question}

Answer:"""

prompt = ChatPromptTemplate(
    messages=["context", "question"],
    template=rag_template
)

# --------------------------------
# RAG QUERY FUNCTION
# --------------------------------
def query_with_rag(user_question, category_filter=None, n_results=3):
    """
    Query ChromaDB and use LangChain LLM to generate answer
    
    Args:
        user_question: The user's question
        category_filter: Optional metadata filter (e.g., {"category": "shipping"})
        n_results: Number of documents to retrieve
    """
    print(f"\n{'='*70}")
    print(f"User Question: {user_question}")
    print(f"{'='*70}")
    
    # Query ChromaDB
    query_params = {
        "query_texts": [user_question],
        "n_results": n_results
    }
    
    if category_filter:
        query_params["where"] = category_filter
        print(f"Filter: {category_filter}")
    
    results = collection.query(**query_params)
    
    # Display retrieved documents
    print(f"\nRetrieved {len(results['documents'][0])} relevant documents:")
    print("-" * 70)
    
    retrieved_docs = []
    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        print(f"\n{i}. [{metadata['category'].upper()}] (similarity: {1-distance:.3f})")
        print(f"   {doc}")
        retrieved_docs.append(doc)
    
    # Combine retrieved documents as context
    context = "\n\n".join(retrieved_docs)
    
    # Generate answer using LangChain
    print(f"\n{'='*70}")
    print("Generating Answer with LLM...")
    print(f"{'='*70}")
    
    messages = [
        SystemMessage(content=context),
        HumanMessage(content=user_question)
    ]
    
    response = model.invoke(messages)
    
    print(f"\nAnswer:\n{response}")
    print(f"\n{'='*70}\n")
    
    return {
        "question": user_question,
        "retrieved_docs": retrieved_docs,
        "answer": response,
        "metadata": results['metadatas'][0]
    }

# --------------------------------
# EXAMPLE QUERIES
# --------------------------------
if __name__ == "__main__":
    
    # Query 1: General question
    query_with_rag("How long does shipping take?")
    
    # Query 2: With metadata filter
    query_with_rag(
        "What payment options do you have?",
        category_filter={"category": "payment"}
    )
    
    # Query 3: Returns question
    query_with_rag("Can I return a product if I don't like it?")
    
    # Query 4: Support question
    query_with_rag("How do I contact customer support?")
    
    # Query 5: Multiple relevant docs
    query_with_rag(
        "Tell me about your policies",
        n_results=5
    )
    
    # --------------------------------
    # INTERACTIVE MODE (Optional)
    # --------------------------------
    print("\n" + "="*70)
    print("Interactive Mode - Ask questions (type 'quit' to exit)")
    print("="*70)
    
    while True:
        user_input = input("\nYour question: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        query_with_rag(user_input)