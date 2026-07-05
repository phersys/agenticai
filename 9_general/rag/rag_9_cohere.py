# pip install cohere python-dotenv

import os
import cohere
from dotenv import load_dotenv

load_dotenv(override=True)

# Read API key from environment
co = cohere.ClientV2(
    api_key=os.getenv("COHERE_API_KEY")
)

# Define the documents
faqs = [
    {
        "text": "Reimbursing Travel Expenses: Easily manage your travel expenses by submitting them through our finance tool. Approvals are prompt and straightforward."
    },
    {
        "text": "Working from Abroad: Working remotely from another country is possible. Simply coordinate with your manager and ensure your availability during core hours."
    },
    {
        "text": "Health and Wellness Benefits: We care about your well-being and offer gym memberships, on-site yoga classes, and comprehensive health insurance."
    },
    {
        "text": "Performance Reviews Frequency: We conduct informal check-ins every quarter and formal performance reviews twice a year."
    },
]

# User query
query = "Are there fitness-related perks?"

# Rerank the documents
results = co.rerank(
    model="rerank-v4.0-pro",
    query=query,
    documents=faqs,
    top_n=1,
)

print(results)

# Pretty-print results
def return_results(results, documents):
    for idx, result in enumerate(results.results):
        print(f"Rank: {idx + 1}")
        print(f"Score: {result.relevance_score}")
        print(f"Document: {documents[result.index]['text']}\n")

return_results(results, faqs)
