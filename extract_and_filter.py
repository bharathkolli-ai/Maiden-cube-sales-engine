import re
import glob
import json

CONSULTANCY_KEYWORDS = [
    "consultancy", "consulting", "solutions", "digital agency", "software agency",
    "staffing", "recruitment", "talent partner", "outsourcing", "technology partner",
    "systems integrator", "professional services", "IT services", "managed services",
]

def parse_linkedin_markdown(text):
    entries = []
    pattern = re.compile(
        r'###\s+(.+?)\s*\n####\s+\[\s*(.+?)\s*\]\(([^)]+)\)\s*\n(.+?)(?=\n\s*\*|\n###|\Z)',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        title, company, company_url, location_block = match.groups()
        entries.append({
            "job_title": title.strip(),
            "company_name": company.strip(),
            "company_url": company_url.strip(),
            "location_raw": location_block.strip().split("\n")[0].strip(),
        })
    return entries

def is_consultancy(company_name):
    name_lower = company_name.lower()
    for kw in CONSULTANCY_KEYWORDS:
        if kw in name_lower:
            return True
    return False

def main():
    all_entries = []
    for filepath in glob.glob("scraped_output_linkedin/attempt_*.md"):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        entries = parse_linkedin_markdown(content)
        all_entries.extend(entries)

    seen = set()
    unique_entries = []
    for e in all_entries:
        key = (e["company_name"], e["job_title"])
        if key not in seen:
            seen.add(key)
            unique_entries.append(e)

    consultancy_matches = [e for e in unique_entries if is_consultancy(e["company_name"])]
    non_matches = [e for e in unique_entries if not is_consultancy(e["company_name"])]

    total = len(unique_entries)
    print(f"Total unique postings: {total}")
    print(f"Consultancy matches: {len(consultancy_matches)}")
    print(f"Non-matches (excluded): {len(non_matches)}")
    if total > 0:
        print(f"Match rate: {len(consultancy_matches) / total * 100:.1f}%")

    print("\n=== CONSULTANCY MATCHES ===")
    for e in consultancy_matches:
        print(f"  {e['company_name']} — {e['job_title']}")

    with open("filtered_consultancies.json", "w", encoding="utf-8") as f:
        json.dump(consultancy_matches, f, indent=2)
    print(f"\nSaved {len(consultancy_matches)} matches to filtered_consultancies.json")

if __name__ == "__main__":
    main()