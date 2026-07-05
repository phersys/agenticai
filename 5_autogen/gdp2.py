import asyncio
import requests
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

load_dotenv(override=True)

# Pydantic models
class EvidenceItem(BaseModel):
    country: str
    quarters: List[str]
    quarterly_growth: List[Optional[float]]
    recessions: List[tuple]
    note: Optional[str] = None

class FactCheckReport(BaseModel):
    claim: str
    verdict: str
    summary: str
    evidence: List[EvidenceItem]
    confidence: str

# FRED series IDs for quarterly real GDP growth
FRED_SERIES = {
    "US": "A191RL1Q225SBEA",  # US Real GDP growth rate
    "IN": "INDNGDPQPSMEI",    # India GDP growth rate
    "GB": "GBRRGDPQDSNAQ",    # UK Real GDP growth rate  
    "JP": "JPNRGDPEXP",       # Japan Real GDP growth rate
}

# Fetch FRED quarterly data
def fetch_fred_quarterly_gdp(series_id: str, start_year: int = 1995):
    """Fetch quarterly GDP growth from FRED API."""
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={requests.utils.os.getenv('FRED_API_KEY')}&file_type=json&observation_start={start_year}-01-01"
    try:
        data = requests.get(url, timeout=20).json()
        if "observations" not in data:
            return [], []
        
        quarters = []
        growths = []
        for obs in data["observations"]:
            if obs["value"] != ".":
                quarters.append(obs["date"])
                growths.append(float(obs["value"]))
        return quarters, growths
    except Exception as e:
        return [], []

# Detect recession (2 consecutive quarters of negative growth)
def detect_recession(quarters: List[str], growths: List[float]):
    """Find periods with 2 consecutive quarters of negative growth (official recession definition)."""
    recessions = []
    i = 0
    while i < len(growths) - 1:
        if growths[i] < 0 and growths[i+1] < 0:
            start = quarters[i]
            end = quarters[i+1]
            # Check if recession continues
            j = i + 2
            while j < len(growths) and growths[j] < 0:
                end = quarters[j]
                j += 1
            recessions.append((start, end))
            i = j
        else:
            i += 1
    return recessions

# Tool for agent
async def check_recession_quarterly(country_code: str, country_name: str) -> EvidenceItem:
    """Check if country had recession using quarterly GDP data (2 consecutive negative quarters)."""
    series_id = FRED_SERIES.get(country_code)
    if not series_id:
        return EvidenceItem(
            country=country_name, 
            quarters=[], 
            quarterly_growth=[], 
            recessions=[],
            note=f"No FRED quarterly data available for {country_name}"
        )
    
    quarters, growths = await asyncio.get_event_loop().run_in_executor(None, fetch_fred_quarterly_gdp, series_id)
    if not quarters:
        return EvidenceItem(
            country=country_name, 
            quarters=[], 
            quarterly_growth=[], 
            recessions=[],
            note="Failed to fetch FRED data"
        )
    
    recessions = detect_recession(quarters, growths)
    note = f"Recessions (2+ consecutive negative quarters): {recessions}" if recessions else "No recessions found"
    
    return EvidenceItem(
        country=country_name, 
        quarters=quarters[-20:],  # Last 20 quarters for brevity
        quarterly_growth=[round(g, 2) for g in growths[-20:]], 
        recessions=recessions,
        note=note
    )

# Create agent
agent = AssistantAgent(
    name="fact_checker",
    model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),
    tools=[check_recession_quarterly],
    system_message="You are a fact-checker. Use quarterly GDP data to verify recession claims (recession = 2 consecutive quarters of negative growth).",
)

# Run fact check
async def main():
    countries = [("US", "United States"), ("IN", "India"), ("GB", "United Kingdom"), ("JP", "Japan")]
    
    # Gather evidence
    evidence = []
    for code, name in countries:
        evidence.append(await check_recession_quarterly(code, name))
    
    # Verdict logic
    india_evidence = next((e for e in evidence if "India" in e.country), None)
    has_recession = india_evidence and len(india_evidence.recessions) > 0
    
    verdict = "Not supported" if has_recession else "Supported"
    summary = f"Using quarterly GDP data from FRED. India {'had' if has_recession else 'had no'} recessions (2+ consecutive negative quarters) in the analyzed period."
    
    report = FactCheckReport(
        claim="India has never faced a recession in last 30 years",
        verdict=verdict,
        summary=summary,
        evidence=evidence,
        confidence="High"
    )
    
    print(report.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())