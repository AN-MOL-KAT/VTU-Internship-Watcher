import sys
from pathlib import Path

# Ensure UTF-8 output stream on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.collector.vtu_scraper import VTUScraper
from src.matching.skill_matcher import SkillMatcher
from src.matching.priority_scorer import PriorityScorer


def test_portal():
    print("==================================================")
    print("         VTU PORTAL CONNECTIVITY & PARSER TEST    ")
    print("==================================================")

    scraper = VTUScraper()
    print(f"\n[1] Testing connection to base URL: {scraper.base_url}")
    listings = scraper.fetch_listings()

    print(f"\n[2] Fetched {len(listings)} listings.")
    print("\n[3] Evaluating sample entries:")

    matcher = SkillMatcher()
    scorer = PriorityScorer()

    for idx, item in enumerate(listings[:5], 1):
        enriched = scraper.fetch_detail(item)
        tech_score, matched_skills = matcher.evaluate_internship(enriched)
        enriched.technical_score = tech_score
        enriched.matched_skills = matched_skills
        p_score, p_level = scorer.calculate_priority(enriched)

        print(f"\n--- Item #{idx} ---")
        print(f"ID:          {enriched.portal_id}")
        print(f"Title:       {enriched.title}")
        print(f"Company:     {enriched.company}")
        print(f"Mode:        {enriched.mode}")
        print(f"Type:        {enriched.internship_type}")
        print(f"Fee:         ₹{enriched.fee}")
        print(f"Stipend:     {enriched.stipend or 'None'}")
        print(f"Match Score: {tech_score}%")
        print(f"Matched:     {', '.join(matched_skills) if matched_skills else 'None'}")
        print(f"Priority:    {p_level} (Score: {p_score})")
        print(f"Status:      {enriched.application_status}")
        print(f"URL:         {enriched.url}")

    print("\n==================================================")
    print("✓ Portal and pipeline test completed successfully!")
    print("==================================================")


if __name__ == "__main__":
    test_portal()
