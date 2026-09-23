from dotenv import load_dotenv
load_dotenv()

import asyncio
import random
import os
import json
import re
from crawl4ai import AsyncWebCrawler
from groq import Groq

groq_client = Groq()

REED_URLS = [
    "https://www.reed.co.uk/jobs/senior-software-engineer-jobs",
    "https://www.reed.co.uk/jobs/full-stack-developer-jobs",
    "https://www.reed.co.uk/jobs/lead-developer-jobs",
    "https://www.reed.co.uk/jobs/engineering-manager-jobs",
]

INDEED_URLS = [
    "https://uk.indeed.com/jobs?q=senior+software+engineer&l=United+Kingdom",
    "https://uk.indeed.com/jobs?q=full+stack+developer&l=United+Kingdom",
]

LINKEDIN_URLS = [
    "https://www.linkedin.com/jobs/search?keywords=Generative%20AI&location=India",
    "https://www.linkedin.com/jobs/search?keywords=Senior%20Software%20Engineer&location=United%20Kingdom",
    "https://www.linkedin.com/jobs/search?keywords=Full%20Stack%20Developer&location=United%20States",
]

CONSULTANCY_SEED_LIST = [
    "endava", "scott logic", "made tech", "equal experts", "codurance",
    "netsol technologies", "eleks", "svitla systems", "railsware",
]

CONSULTANCY_KEYWORDS = [
    "consultancy", "consulting", "digital agency", "software agency",
    "systems integrator", "professional services", "IT services",
    "managed services", "technology partner",
]

TOTAL_REQUESTS = 10
DELAY_SECONDS = 3

USE_MOCK_LLM = False

os.makedirs("stage1_output", exist_ok=True)

PROMPT_TEMPLATE = """Extract and analyze the job and recruiter details from the scraped page content below.
Strictly return ONLY a valid raw JSON object (no markdown formatting, no ```json fences, no preamble, no commentary) matching this schema:

{{
  "recruiter": {{
    "name": "Name of recruiter or 'Not Disclosed'",
    "linkedin_profile": "URL or 'Not Disclosed'",
    "designation": "Designation or 'Not Disclosed'",
    "company": "Company Name",
    "location": "Location or 'Not Disclosed'",
    "professional_summary": "Short 1-sentence recruitment focus summary"
  }},
  "job_posting": {{
    "job_title": "Title of the position",
    "technology_hiring_for": "Core technical focus e.g. Generative AI",
    "technology_stack": ["Skill1", "Skill2"],
    "experience_required": "e.g. 5-8 Years",
    "location": "Job Location",
    "employment_type": "Full Time / Contract / Part Time",
    "number_of_openings": 1,
    "salary": "Salary or 'Not Disclosed'",
    "posted_date": "Posting date / age",
    "job_description": "Brief summary of the role"
  }},
  "hiring_intelligence": {{
    "hiring_priority": "High / Medium / Low",
    "technology_focus": "Specific tech specialty",
    "recruitment_type": "Lateral Hiring / Campus / Contract",
    "estimated_hiring_volume": "High / Medium / Low",
    "demand_score": 85
  }}
}}

Scraped Content:
{content}
"""


def is_consultancy(company_name):
    if not company_name:
        return False, None
    name_lower = company_name.lower()
    if any(seed in name_lower for seed in CONSULTANCY_SEED_LIST):
        return True, "seed_list"
    if any(kw in name_lower for kw in CONSULTANCY_KEYWORDS):
        return True, "keyword"
    return False, None


def extract_fields_mock(raw_text, source_url):
    return {
        "recruiter": {
            "name": "Anjali Sharma",
            "linkedin_profile": "https://linkedin.com/in/xxxxx",
            "designation": "Senior Talent Acquisition Specialist",
            "company": "Microsoft",
            "location": "Hyderabad, India",
            "professional_summary": "Hiring for AI, Data Engineering and Cloud roles"
        },
        "job_posting": {
            "job_title": "Senior GenAI Engineer",
            "technology_hiring_for": "Generative AI",
            "technology_stack": ["Python", "CrewAI", "LangGraph", "Azure OpenAI", "RAG", "FastAPI"],
            "experience_required": "5-8 Years",
            "location": "Hyderabad",
            "employment_type": "Full Time",
            "number_of_openings": 15,
            "salary": "Not Disclosed",
            "posted_date": "2 Days Ago",
            "job_description": "..."
        },
        "hiring_intelligence": {
            "hiring_priority": "High",
            "technology_focus": "Generative AI",
            "recruitment_type": "Lateral Hiring",
            "estimated_hiring_volume": "High",
            "demand_score": 92
        }
    }


# ============================================================
# LLM PROVIDER — swap this function to change model/provider.
# Everything else in the pipeline stays the same.
# ============================================================
def call_llm(prompt):
    """
    Currently uses Groq (openai/gpt-oss-120b).
    To switch providers, replace the body of this function only —
    it must return the raw text response from the model.
    """
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content.strip()


def extract_fields_with_llm(raw_text, source_url):
    prompt = PROMPT_TEMPLATE.format(content=raw_text[:6000])
    try:
        text = call_llm(prompt)
        text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f"Error during LLM extraction: {e}")
        return None


async def scrape_one(url):
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        return result.markdown if result.markdown else ""


async def main():
    all_urls = (
        [(u, "reed") for u in REED_URLS]
        + [(u, "indeed") for u in INDEED_URLS]
        + [(u, "linkedin") for u in LINKEDIN_URLS]
    )
    final_records = []

    for i in range(1, TOTAL_REQUESTS + 1):
        url, source = random.choice(all_urls)
        print(f"[{i}/{TOTAL_REQUESTS}] Scraping from {source.upper()}: {url}")
        content = await scrape_one(url)

        if len(content) < 1500:
            print("Content too short or crawler blocked, skipping...")
            await asyncio.sleep(DELAY_SECONDS)
            continue

        if USE_MOCK_LLM:
            extracted = extract_fields_mock(content, url)
        else:
            extracted = extract_fields_with_llm(content, url)

        if not extracted or not extracted.get("job_posting", {}).get("job_title"):
            print("Failed to extract valid job posting schema, skipping...")
            await asyncio.sleep(DELAY_SECONDS)
            continue

        company = extracted.get("recruiter", {}).get("company") or ""
        matched, match_type = is_consultancy(company)

        extracted["source_platform"] = source
        extracted["source_url"] = url
        extracted["is_consultancy_match"] = matched
        extracted["match_type"] = match_type

        final_records.append(extracted)
        print(f"Successfully processed job from: {company}")
        await asyncio.sleep(DELAY_SECONDS)

    output_file = "stage1_output/results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2)

    print(f"\nDone! {len(final_records)} records saved to {output_file}")
    return final_records


if __name__ == "__main__":
    asyncio.run(main())
