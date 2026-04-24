"""
AI Job Application Agent – CLI Mode
Run the full pipeline from the command line without the web UI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import Config
from database.models import Database
from utils.resume_parser import parse_resume

Config.ensure_dirs()
db = Database()


def print_banner():
    print("\n" + "=" * 60)
    print("  🤖 AI Job Application Agent – CLI Mode")
    print("=" * 60)


def upload_resume():
    """Upload and parse a resume file."""
    path = input("\n📄 Enter path to your resume (PDF/DOCX/TXT): ").strip().strip('"')
    if not os.path.exists(path):
        print("  ❌ File not found!")
        return

    try:
        parsed = parse_resume(path)
        db.save_resume(
            file_name=os.path.basename(path),
            file_path=path,
            raw_text=parsed["raw_text"],
            skills=parsed["skills"]
        )
        print(f"\n  ✅ Resume uploaded: {os.path.basename(path)}")
        print(f"  📊 Skills found ({len(parsed['skills'])}): {', '.join(parsed['skills'])}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


def scrape_jobs():
    """Scrape jobs from LinkedIn and/or Internshala."""
    query = input("\n🔍 Job search query (e.g. 'Python Developer'): ").strip()
    location = input("📍 Location (default: India): ").strip() or "India"

    print("\n  Sources:")
    print("  1. LinkedIn")
    print("  2. Internshala")
    print("  3. Both")
    choice = input("  Choose (1/2/3, default: 1): ").strip() or "1"

    total = 0

    if choice in ("1", "3"):
        print("\n  🔗 Scraping LinkedIn...")
        try:
            from scraper.linkedin_scraper import LinkedInScraper
            scraper = LinkedInScraper()
            jobs = scraper.scrape_jobs(query, location)
            count = db.add_jobs_bulk(jobs)
            print(f"  ✅ LinkedIn: Found {len(jobs)} jobs, {count} new saved")
            total += count
        except Exception as e:
            print(f"  ❌ LinkedIn error: {e}")

    if choice in ("2", "3"):
        print("\n  🎓 Scraping Internshala...")
        try:
            from scraper.internshala_scraper import InternShalaScraper
            scraper = InternShalaScraper()
            jobs = scraper.scrape_jobs(query, location)
            count = db.add_jobs_bulk(jobs)
            print(f"  ✅ Internshala: Found {len(jobs)} jobs, {count} new saved")
            total += count
        except Exception as e:
            print(f"  ❌ Internshala error: {e}")

    print(f"\n  📊 Total new jobs saved: {total}")


def ai_match():
    """Run AI matching on unprocessed jobs."""
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith("sk-your"):
        print("\n  ❌ OpenAI API key not set. Add it to .env first.")
        return

    resume = db.get_active_resume()
    if not resume:
        print("\n  ❌ No resume uploaded. Upload one first (option 1).")
        return

    from agent.agent import JobApplicationAgent
    print("\n  🤖 Starting AI agent...")
    agent = JobApplicationAgent()
    print("  ⏳ Matching jobs against your resume... (this takes 1-2 minutes)")

    result = agent.quick_match()

    if result["success"]:
        print(f"\n  ✅ Done!\n")
        print("  " + "-" * 50)
        print(result["output"])
        print("  " + "-" * 50)
    else:
        print(f"\n  ❌ {result['output']}")


def ai_chat():
    """Interactive chat with the AI agent."""
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith("sk-your"):
        print("\n  ❌ OpenAI API key not set. Add it to .env first.")
        return

    from agent.agent import JobApplicationAgent
    print("\n  🤖 Starting AI agent... (type 'quit' to exit)")
    agent = JobApplicationAgent()
    print("  ✅ Agent ready! Ask me anything about your job search.\n")

    while True:
        user_input = input("  You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("  👋 Goodbye!")
            break
        if not user_input:
            continue

        print("  🤖 Thinking...")
        result = agent.run(user_input)
        print(f"\n  Agent: {result['output']}\n")

        if result.get("steps"):
            print(f"  🔧 Actions taken: {', '.join(s['tool'] for s in result['steps'])}\n")


def view_stats():
    """Show current stats."""
    stats = db.get_stats()
    resume = db.get_active_resume()

    print(f"\n  {'=' * 40}")
    print(f"  📊 Dashboard Stats")
    print(f"  {'=' * 40}")
    print(f"  💼 Jobs Scraped:      {stats['total_jobs']}")
    print(f"  📋 Applications:      {stats['total_applications']}")
    print(f"  🎯 Avg Match Score:   {stats['avg_match_score']:.0%}")
    print(f"  📄 Resume:            {'✅ ' + resume['file_name'] if resume else '❌ Not uploaded'}")

    if stats["status_breakdown"]:
        print(f"\n  Pipeline Breakdown:")
        for status, count in stats["status_breakdown"].items():
            print(f"    {status:20s} → {count}")

    if stats["source_breakdown"]:
        print(f"\n  Jobs by Source:")
        for source, count in stats["source_breakdown"].items():
            print(f"    {source:20s} → {count}")


def view_applications():
    """View all applications with scores."""
    apps = db.get_applications()
    if not apps:
        print("\n  📋 No applications yet. Run AI Match first.")
        return

    print(f"\n  {'=' * 70}")
    print(f"  {'#':<4} {'Job Title':<30} {'Company':<20} {'Score':<8} {'Status'}")
    print(f"  {'-' * 70}")

    for app in apps:
        score_pct = f"{app['match_score']:.0%}"
        title = app['title'][:28] if app.get('title') else 'N/A'
        company = app['company'][:18] if app.get('company') else 'N/A'
        status = app['status'].replace('_', ' ').title()
        print(f"  {app['id']:<4} {title:<30} {company:<20} {score_pct:<8} {status}")

    print(f"  {'=' * 70}")
    print(f"  Total: {len(apps)} applications\n")


def full_pipeline():
    """Run the full pipeline: scrape → match → cover letters."""
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith("sk-your"):
        print("\n  ❌ OpenAI API key not set. Add it to .env first.")
        return

    resume = db.get_active_resume()
    if not resume:
        print("\n  ❌ No resume uploaded. Upload one first (option 1).")
        return

    query = input("\n🔍 Job search query: ").strip()
    location = input("📍 Location (default: India): ").strip() or "India"

    from agent.agent import JobApplicationAgent
    print("\n  🤖 Starting full pipeline...")
    print("  ⏳ This will: Scrape → Match → Generate Cover Letters")
    print("  ☕ Grab a coffee, this takes a few minutes...\n")

    agent = JobApplicationAgent()
    result = agent.scrape_and_match(query, location=location)

    if result["success"]:
        print(f"\n  ✅ Pipeline complete!\n")
        print("  " + "-" * 50)
        print(result["output"])
        print("  " + "-" * 50)
    else:
        print(f"\n  ❌ {result['output']}")


def main():
    print_banner()

    while True:
        print("\n  ┌─────────────────────────────────┐")
        print("  │  1. 📄 Upload Resume            │")
        print("  │  2. 🔍 Scrape Jobs              │")
        print("  │  3. 🤖 AI Match Jobs            │")
        print("  │  4. 💬 Chat with Agent           │")
        print("  │  5. 📊 View Stats               │")
        print("  │  6. 📋 View Applications        │")
        print("  │  7. ⚡ Full Pipeline             │")
        print("  │  0. 🚪 Exit                     │")
        print("  └─────────────────────────────────┘")

        choice = input("\n  Choose an option: ").strip()

        if choice == "1":
            upload_resume()
        elif choice == "2":
            scrape_jobs()
        elif choice == "3":
            ai_match()
        elif choice == "4":
            ai_chat()
        elif choice == "5":
            view_stats()
        elif choice == "6":
            view_applications()
        elif choice == "7":
            full_pipeline()
        elif choice == "0":
            print("\n  👋 Goodbye! Good luck with your job search!\n")
            break
        else:
            print("  ❌ Invalid choice. Try again.")


if __name__ == "__main__":
    main()
