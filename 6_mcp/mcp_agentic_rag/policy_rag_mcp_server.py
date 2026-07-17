# pip install mcp langchain-chroma langchain-huggingface langchain-community pypdf sentence-transformers
#
# MCP server for the company policy assistant demo. This server does no
# reasoning at all - it only loads/chunks/embeds/stores/retrieves text. Every
# decision about *which* tool to call, *what* to search for, and how to
# combine or summarize results is made by the LangGraph agent (in
# policy_rag_agent.py), which is the only place an LLM is invoked.
#
# Storage model: one PDF = one Chroma collection = one document_id. The
# document_id/collection name is a slug derived from the filename, e.g.
# "Travel Policy.pdf" -> "travel_policy". search_collection() resolves loose
# names like "Travel" to the real slug via case-insensitive substring
# matching - that's plain string comparison, not reasoning.
import json
import os
import re

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

mcp = FastMCP("PolicyRAG")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


def slugify(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return name


def get_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def similarity_search_with_retry(collection_name: str, query: str, top_k: int):
    # Chroma's PersistentClient can transiently fail with "Nothing found on
    # disk" the first time a collection's HNSW index is touched in a fresh
    # process (observed once right after a batch of bootstrap writes). One
    # retry against a freshly-fetched vectorstore handle clears it.
    last_error = None
    for _ in range(2):
        try:
            vectorstore = get_vectorstore(collection_name)
            return vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
        except Exception as e:
            last_error = e
    raise last_error


def resolve_collection(collection: str) -> str | None:
    existing = [c.name for c in chroma_client.list_collections()]
    needle = collection.strip().lower().replace(" ", "_")

    for name in existing:
        if name == needle:
            return name
    for name in existing:
        if needle in name or name in needle:
            return name
    return None


@mcp.tool()
def store_document(file_path: str) -> dict:
    """
    Loads a PDF, splits it into chunks, embeds them, and stores them in a
    Chroma collection dedicated to that document. Re-running this on the same
    file replaces the existing collection with freshly stored chunks.
    Args:
    file_path: path to the PDF file, absolute or relative to the data/ directory
    """
    try:
        full_path = file_path if os.path.isabs(file_path) else os.path.join(DATA_DIR, file_path)
        if not os.path.exists(full_path):
            return {"error": f"File not found: {full_path}"}

        filename = os.path.basename(full_path)
        document_id = slugify(filename)

        loader = PyPDFLoader(full_path)
        pages = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
        chunks = splitter.split_documents(pages)

        for i, chunk in enumerate(chunks):
            chunk.metadata["document_id"] = document_id
            chunk.metadata["source_file"] = filename
            chunk.metadata["chunk_index"] = i

        try:
            chroma_client.delete_collection(document_id)
        except Exception:
            pass

        vectorstore = get_vectorstore(document_id)
        vectorstore.add_documents(chunks)

        return {
            "status": "stored",
            "document_id": document_id,
            "collection": document_id,
            "source_file": filename,
            "chunks_stored": len(chunks),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_collections() -> str:
    """
    Lists every policy document currently stored, one entry per Chroma
    collection (one collection per source PDF). Returns a JSON array (as a
    string) of {document_id, source_file, chunk_count}.
    """
    results = []
    for c in chroma_client.list_collections():
        collection = chroma_client.get_collection(c.name)
        count = collection.count()
        sample = collection.peek(limit=1)
        source_file = None
        if sample and sample.get("metadatas") and sample["metadatas"]:
            source_file = sample["metadatas"][0].get("source_file")
        results.append({
            "document_id": c.name,
            "source_file": source_file,
            "chunk_count": count,
        })
    return json.dumps(results)


@mcp.tool()
def search_documents(query: str, top_k: int = 5) -> str:
    """
    Searches across every stored policy document and returns the best
    matching chunks regardless of which document they came from. Returns a
    JSON array (as a string) of {document_id, source_file, chunk_text, score}.
    Args:
    query: the search query text
    top_k: maximum number of results to return
    """
    all_results = []
    for c in chroma_client.list_collections():
        try:
            hits = similarity_search_with_retry(c.name, query, top_k)
        except Exception:
            continue
        for doc, score in hits:
            all_results.append({
                "document_id": doc.metadata.get("document_id", c.name),
                "source_file": doc.metadata.get("source_file"),
                "chunk_text": doc.page_content,
                "score": score,
            })

    all_results.sort(key=lambda r: r["score"], reverse=True)
    return json.dumps(all_results[:top_k])


@mcp.tool()
def search_collection(collection: str, query: str, top_k: int = 5) -> str:
    """
    Searches within a single named policy document/collection only. Returns
    a JSON array (as a string) of {document_id, source_file, chunk_text, score}.
    Args:
    collection: document_id or a loose name (e.g. "Travel") to resolve to a stored collection
    query: the search query text
    top_k: maximum number of results to return
    """
    resolved = resolve_collection(collection)
    if resolved is None:
        return json.dumps([{"error": f"No collection matching '{collection}'. Call list_collections() to see available documents."}])

    hits = similarity_search_with_retry(resolved, query, top_k)

    return json.dumps([
        {
            "document_id": resolved,
            "source_file": doc.metadata.get("source_file"),
            "chunk_text": doc.page_content,
            "score": score,
        }
        for doc, score in hits
    ])


@mcp.tool()
def get_document(document_id: str) -> dict:
    """
    Returns metadata and a short preview for a single stored document -
    useful for confirming a document exists before deciding what to do with it.
    Args:
    document_id: the document_id (collection name) to look up
    """
    resolved = resolve_collection(document_id)
    if resolved is None:
        return {"error": f"No document matching '{document_id}'. Call list_collections() to see available documents."}

    collection = chroma_client.get_collection(resolved)
    count = collection.count()
    data = collection.get(limit=1)
    source_file = data["metadatas"][0].get("source_file") if data["metadatas"] else None
    preview = data["documents"][0][:300] if data["documents"] else ""

    return {
        "document_id": resolved,
        "source_file": source_file,
        "chunk_count": count,
        "preview": preview,
    }


@mcp.tool()
def summarize_document(document_id: str) -> dict:
    """
    Returns the full reconstructed text of a stored document, in chunk order,
    so the calling agent can generate its own summary. This tool does not
    summarize anything itself - it only retrieves the raw text.
    Args:
    document_id: the document_id (collection name) to retrieve
    """
    resolved = resolve_collection(document_id)
    if resolved is None:
        return {"error": f"No document matching '{document_id}'. Call list_collections() to see available documents."}

    collection = chroma_client.get_collection(resolved)
    data = collection.get()

    ordered = sorted(
        zip(data["metadatas"], data["documents"]),
        key=lambda pair: pair[0].get("chunk_index", 0),
    )
    full_text = "\n\n".join(doc for _, doc in ordered)

    return {
        "document_id": resolved,
        "source_file": ordered[0][0].get("source_file") if ordered else None,
        "full_text": full_text,
    }


if __name__ == "__main__":
    mcp.run()
