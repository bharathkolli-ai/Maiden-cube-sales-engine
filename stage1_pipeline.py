from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import random
import re
from crawl4ai import AsyncWebCrawler
from huggingface_hub import InferenceClient

# Initialize Hugging Face Client (reads HF_TOKEN from environment/.env)
hf_client = InferenceClient(
    token=os.getenv("HF_TOKEN")
)

MODEL_ID = "meta-llama/Llama-3.3-70B-Instruct"

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
    "systems integrator", "professional services", "it services",
    "managed services", "technology partner",
]

TOTAL_REQUESTS = 10
DELAY_SECONDS = 3
OUTPUT_DIR = "stage1_output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "results.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPT_TEMPLATE = """Extract and analyze the job and recruiter details from the scraped web content below.
Strictly return ONLY a valid raw JSON object matching the exact schema below (no markdown fences, no code blocks, no preamble, no commentary).

{{
  "recruiter": {{
    "name": "Name of recruiter or 'Not Disclosed'",
    "linkedin_profile": "Recruiter profile URL or 'Not Disclosed'",
    "designation": "Designation / Role or 'Not Disclosed'",
    "company": "Company Name",
    "location": "Location or 'Not Disclosed'",
    "professional_summary": "1-sentence summary of hiring focus"
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


def is_consultancy(company_name: str):
    if not company_name or company_name.strip().lower() == "not disclosed":
        return False, None
    name_lower = company_name.lower()
    if any(seed in name_lower for seed in CONSULTANCY_SEED_LIST):
        return True, "seed_list"
    if any(kw in name_lower for kw in CONSULTANCY_KEYWORDS):
        return True, "keyword"
    return False, None


def extract_fields_with_llm(raw_text: str):
    prompt = PROMPT_TEMPLATE.format(content=raw_text[:6000])
    try:
        response = hf_client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.1,
        )
        text = response.choices[0].message.content.strip()
        # Clean markdown code backticks if the model includes them
        text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f"Error during Hugging Face LLM extraction: {e}")
        return None


async def scrape_one(url: str) -> str:
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

        # Skip anti-bot challenge pages or empty crawls
        if len(content) < 1500:
            print("Content too short or bot block encountered. Skipping...")
            await asyncio.sleep(DELAY_SECONDS)
            continue

        extracted = extract_fields_with_llm(content)

        # Ensure valid response and that a job title was actually detected
        if not extracted or not extracted.get("job_posting", {}).get("job_title"):
            print("Extraction empty or malformed. Skipping...")
            await asyncio.sleep(DELAY_SECONDS)
            continue

        company = extracted.get("recruiter", {}).get("company", "")[cite: 2]
        matched, match_type = is_consultancy(company)

        # Append source tracking & consultancy detection
        extracted["source_platform"] = source
        extracted["source_url"] = url
        extracted["is_consultancy_match"] = matched
        extracted["match_type"] = match_type

        final_records.append(extracted)
        print(f"Successfully processed role: {extracted['job_posting']['job_title']} at {company}")[cite: 2]

        await asyncio.sleep(DELAY_SECONDS)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2)

    print(f"\nExecution complete. Saved {len(final_records)} records to {OUTPUT_FILE}")
    return final_records


if __name__ == "__main__":
    asyncio.run(main())
