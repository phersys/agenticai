# pip install tavily-python langchain-tavily
# Also add TAVILY_API_KEY to .env file
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_tavily import TavilySearch
from langchain.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv(override=True)

# LLM
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1
)

# TOOL
tool = TavilySearch(max_results=5, topic="general")

my_agent = create_agent(
    model=model,
    tools=[tool],
    system_prompt=SystemMessage(
        content="You are an assistant. Use the search tool when needed."
    )
)

# INVOKE
response = my_agent.invoke({
    "messages": [
        HumanMessage(content="Give me 5 latest news about AI")
    ]
})

print(response["messages"][-1].content)
