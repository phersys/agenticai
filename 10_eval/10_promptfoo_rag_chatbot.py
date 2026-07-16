"""
Simple RAG banking chatbot, used as a promptfoo custom Python provider.

No LLM normalization, no short-term memory -- just embed the question,
find the closest FAQ entry in Chroma, and return its answer if the match
is confident enough. Kept deliberately simple/stateless so promptfoo can
call it once per test case without one test's state leaking into another.

Reuses the same banking_chromadb_eval vector database built by
10_prompt_regression_chainforge_eval.py's sibling RAG scripts, so
promptfoo is testing the real retrieval pipeline, not a raw LLM call.

promptfoo calls call_api(prompt, options, context) once per test case;
`prompt` is the rendered {{question}} text.
"""

import os

# The embedding model is already cached locally (~/.cache/huggingface) --
# skip the network HEAD-request freshness check so a slow/unreachable
# huggingface.co doesn't stall or fail this script with read timeouts.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import pandas as pd
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings

load_dotenv(override=True)

VECTOR_DISTANCE_THRESHOLD = 0.7

# 3_langgraph/Dataset_Banking_chatbot.csv contains a couple of planted
# discriminatory rows (bias-testing bait). Distance-based retrieval alone
# can't tell a safe match from an unsafe one, so block known-bad answers
# by content before they're ever returned.
BLOCKED_RESPONSE_SUBSTRINGS = [
    "only serve rich people",
    "not welcome at our bank",
]

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "3_langgraph", "Dataset_Banking_chatbot.csv")
PERSIST_DIR = os.path.join(BASE_DIR, "banking_chromadb_eval")
COLLECTION_NAME = "chroma_bank_faq"

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

client = chromadb.PersistentClient(path=PERSIST_DIR, settings=Settings())

# If collection already exists, use it
if COLLECTION_NAME in [c.name for c in client.list_collections()]:
    vectordb = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )
else: # If collection doesn't exist, create it
    df = pd.read_csv(CSV_PATH, encoding="latin-1")
    texts = df["Query"].astype(str).tolist()
    metadatas = df[["Query", "Response"]].to_dict(orient="records")
    vectordb = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR
    )

def answer_question(question: str) -> str:
    results = vectordb.similarity_search_with_score(question, k=1)
    if not results:
        return "I'm sorry, I couldn't find an answer for that."

    doc, distance = results[0]
    if distance > VECTOR_DISTANCE_THRESHOLD:
        return "I'm sorry, I couldn't find an answer for that."

    answer = doc.metadata["Response"]
    if any(s.lower() in answer.lower() for s in BLOCKED_RESPONSE_SUBSTRINGS):
        return "I'm sorry, I couldn't find an answer for that."

    return answer

# Entry point promptfoo calls for each test case
def call_api(prompt, options, context):
    return {"output": answer_question(prompt)}

if __name__ == "__main__":
    print("Simple Banking FAQ RAG Chatbot")
    print("Type 'exit' to quit\n")

    while True:
        q = input("You: ").strip()
        if q.lower() == "exit":
            break
        print(f"Bot: {answer_question(q)}\n")
