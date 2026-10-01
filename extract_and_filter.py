import json
import os

INPUT_FILE = "stage1_output/results.json"
OUTPUT_FILE = "filtered_consultancies.json"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file '{INPUT_FILE}' not found. Run the scraper first.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        try:
            records = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{INPUT_FILE}'.")
            return

    # Deduplicate based on (company, job_title)
    seen = set()
    unique_records = []

    for item in records:
        company = item.get("recruiter", {}).get("company", "").strip()
        job_title = item.get("job_posting", {}).get("job_title", "").strip()

        # Fallback if fields are missing
        if not job_title:
            continue

        key = (company.lower(), job_title.lower())
        if key not in seen:
            seen.add(key)
            unique_records.append(item)

    # Filter based on the match already flagged by the pipeline
    consultancy_matches = [e for e in unique_records if e.get("is_consultancy_match")]
    non_matches = [e for e in unique_records if not e.get("is_consultancy_match")]

    total = len(unique_records)
    print(f"Total unique postings: {total}")
    print(f"Consultancy matches: {len(consultancy_matches)}")
    print(f"Non-matches (excluded): {len(non_matches)}")
    if total > 0:
        print(f"Match rate: {len(consultancy_matches) / total * 100:.1f}%")

    print("\n=== CONSULTANCY MATCHES ===")
    for e in consultancy_matches:
        comp = e.get("recruiter", {}).get("company", "Unknown")
        title = e.get("job_posting", {}).get("job_title", "Unknown")
        match_type = e.get("match_type", "n/a")
        print(f"  {comp} — {title} (matched via: {match_type})")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(consultancy_matches, f, indent=2)

    print(f"\nSaved {len(consultancy_matches)} matches to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
