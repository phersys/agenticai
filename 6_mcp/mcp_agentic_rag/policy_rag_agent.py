# pip install langgraph langchain-ollama langchain-core mcp
# Also run generate_sample_data.py once first to create the sample PDFs in data/
#
# The agent: this is the only place an LLM is invoked. It decides which MCP
# tool to call and when, based on the user's question - policy_rag_mcp_server.py
# itself never reasons, it just stores/retrieves text on request.
import asyncio
import json
import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SERVER_SCRIPT = os.path.join(BASE_DIR, "policy_rag_mcp_server.py")

SYSTEM_PROMPT = """You are a company policy assistant for employees.

You have tools to search and retrieve company policy documents stored as
separate collections: HR, Leave, Travel, Expense, IT Security, Code of
Conduct, Remote Work, Benefits, Laptop, and Medical Insurance policies.

Guidelines:
- If you have a strong guess which single policy area is relevant, call
  search_collection with that policy name and the user's question.
- If a question could span multiple policies (e.g. a resignation question
  might involve both Leave and HR policies), call search_collection multiple
  times, once per relevant policy, and combine the results in your answer.
- If you are not sure which policy is relevant, call search_documents to
  search across everything, or list_collections to see what's available.
- If the user asks for an overview or summary of a whole policy, call
  summarize_document and write the summary yourself from the returned text.
- Always mention which policy document(s) you based your answer on.
- If nothing relevant is found, say so plainly instead of guessing.
"""


def make_tools(session: ClientSession):
    @tool
    async def store_document(file_path: str) -> str:
        """Load a PDF, chunk it, embed it, and store it as a new policy collection."""
        result = await session.call_tool("store_document", {"file_path": file_path})
        return result.content[0].text

    @tool
    async def list_collections() -> str:
        """List every policy document currently stored."""
        result = await session.call_tool("list_collections", {})
        return result.content[0].text

    @tool
    async def search_documents(query: str, top_k: int = 5) -> str:
        """Search across every stored policy document for the given query."""
        result = await session.call_tool("search_documents", {"query": query, "top_k": top_k})
        return result.content[0].text

    @tool
    async def search_collection(collection: str, query: str, top_k: int = 5) -> str:
        """Search within one named policy document/collection (e.g. 'Travel', 'Leave', 'HR')."""
        result = await session.call_tool(
            "search_collection", {"collection": collection, "query": query, "top_k": top_k}
        )
        return result.content[0].text

    @tool
    async def get_document(document_id: str) -> str:
        """Get metadata and a short preview for a single stored policy document."""
        result = await session.call_tool("get_document", {"document_id": document_id})
        return result.content[0].text

    @tool
    async def summarize_document(document_id: str) -> str:
        """Get the full text of a stored policy document so you can summarize it yourself."""
        result = await session.call_tool("summarize_document", {"document_id": document_id})
        return result.content[0].text

    return [
        store_document,
        list_collections,
        search_documents,
        search_collection,
        get_document,
        summarize_document,
    ]


async def bootstrap_ingestion(session: ClientSession):
    result = await session.call_tool("list_collections", {})
    existing = json.loads(result.content[0].text)
    existing_files = {entry.get("source_file") for entry in existing if entry.get("source_file")}

    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    for filename in pdf_files:
        if filename in existing_files:
            continue
        print(f"[bootstrap] storing {filename} ...")
        await session.call_tool("store_document", {"file_path": filename})
    print(f"[bootstrap] {len(pdf_files)} policy document(s) available.\n")


PLAN_PROMPT = """A user asked a company policy assistant this question:

"{query}"

The available policy areas are: HR, Leave, Travel, Expense, IT Security,
Code of Conduct, Remote Work, Benefits, Laptop, Medical Insurance.

In 1-2 short sentences, state which policy area(s) you think are relevant
and why. Do not answer the user's question itself, just state your plan."""


async def show_plan(llm, query: str):
    # llama3.2's tool-calling responses come back with empty `content` (verified
    # empirically) - it only emits tool_calls, no free-text rationale. So the
    # "why" has to come from a separate, non-tool-bound call before the agent
    # touches any tools, purely so the class can see the reasoning behind the
    # tool choices that follow.
    plan = await llm.ainvoke(PLAN_PROMPT.format(query=query))
    print(f"Plan: {plan.content}\n")


def print_new_messages(messages, printed_count: int) -> int:
    for msg in messages[printed_count:]:
        if getattr(msg, "type", None) == "ai":
            for call in getattr(msg, "tool_calls", None) or []:
                print(f"  -> calling {call['name']}({call['args']})")
        elif getattr(msg, "type", None) == "tool":
            preview = str(msg.content)[:200]
            print(f"     result: {preview}")
    return len(messages)


async def main():
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await bootstrap_ingestion(session)

            tools = make_tools(session)
            llm = ChatOllama(model="llama3.2", temperature=0.1)
            agent = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)

            print("Company Policy Assistant - ask a question (or type 'exit')\n")
            history = []
            while True:
                query = input("You: ").strip()
                if query.lower() in ("exit", "quit"):
                    break
                if not query:
                    continue

                await show_plan(llm, query)

                history.append({"role": "user", "content": query})
                printed_count = len(history)
                final_state = None

                async for state in agent.astream({"messages": history}, stream_mode="values"):
                    final_state = state
                    printed_count = print_new_messages(state["messages"], printed_count)

                final_message = final_state["messages"][-1]
                print(f"\nAssistant: {final_message.content}\n")

                history = final_state["messages"]


if __name__ == "__main__":
    asyncio.run(main())
