# -------------------------------
# 1. Install dependencies if needed
# -------------------------------
# pip install llama-index openai

# -------------------------------
# 2. Imports
# -------------------------------
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

# -------------------------------
# 3. Configure LLM (NEW WAY)
# -------------------------------
# LLM is used for Answer synthesis, Context compression, Reasoning over retrieved chunks
Settings.llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0,
    # api_key=os.getenv("OPENAI_API_KEY"),
)

# -------------------------------
# 4. Load the text file as a document
# -------------------------------
# Read the text file and wrap it in a Document object
# No chunking yet — that happens during indexing
# Even though it’s a single file, LlamaIndex treats it as a collection of documents
documents = SimpleDirectoryReader(
    input_files=[
        r"C:\code\agenticai\3_langgraph\darwin\Origin-of-Species.txt"
    ]
).load_data()

# -------------------------------
# 5. Build Vector Index
# -------------------------------
# Internally, Llamaindex  ...
# Step 1: Splits the book into smaller chunks (~512 tokens by default)
# Adds overlap for context continuity
# e.g. Chunk 1 → Chapter 1 paragraphs, Chunk 2 → Next section
# Step 2: Embedding: Each chunk -> Vector embedding
# e.g. Text chunk → [0.023, -0.91, 0.44, ...]
# Step 3: Store all embeddings as in-memory vector database
index = VectorStoreIndex.from_documents(documents)

# Create a query engine
# Builds a retrieval + reasoning (synthesis) chain
# This is RAG, although we have not manually implemented it:
# User question -> Embed question -> Similarity search (top-k)
# -> Send chunks to LLM -> Generate final answer
query_engine = index.as_query_engine()

# -------------------------------
# 6. Query Examples
# -------------------------------
# Per query: (1) Query is embedded, 
# (2) Similar chunks from the Darwin book are retrived
# (3) LLM receives: Retrieved text and our question
# (4) LLM synthesizes final answer grounded in the book
query1 = "Summarize the main ideas of the book."
query2 = "What examples of natural selection are mentioned?"

response1 = query_engine.query(query1)
response2 = query_engine.query(query2)

print("Query 1 Result:\n", response1)
print("\nQuery 2 Result:\n", response2)
