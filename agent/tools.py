"""
LangChain Agent Tools – Custom tools the agent uses to perform its tasks.
Each tool is a self-contained function that the agent can invoke.
"""

import json
import os
import logging
from datetime import datetime
from langchain.tools import tool

from database.models import Database
from scraper.linkedin_scraper import LinkedInScraper
from scraper.internshala_scraper import InternShalaScraper
from config import Config

logger = logging.getLogger(__name__)
db = Database()


@tool
def scrape_linkedin_jobs(query: str, location: str = "India") -> str:
    """
    Scrape job listings from LinkedIn based on search query and location.
    Use this when you need to find new job opportunities on LinkedIn.

    Args:
        query: Job title or keywords (e.g. "Python Developer", "Data Scientist")
        location: Location to filter by (e.g. "India", "Remote", "Bangalore")

    Returns:
        JSON string with scraped job listings
    """
    try:
        scraper = LinkedInScraper()
        jobs = scraper.scrape_jobs(query, location)
        count = db.add_jobs_bulk(jobs)
        return json.dumps({
            "status": "success",
            "jobs_found": len(jobs),
            "new_jobs_saved": count,
            "source": "LinkedIn",
            "sample_jobs": jobs[:5]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def scrape_internshala_jobs(query: str, location: str = "") -> str:
    """
    Scrape internship and job listings from Internshala.
    Use this when you need to find internships or entry-level positions.

    Args:
        query: Job/internship keywords (e.g. "python", "web development")
        location: Optional location filter

    Returns:
        JSON string with scraped listings
    """
    try:
        scraper = InternShalaScraper()
        jobs = scraper.scrape_jobs(query, location)
        count = db.add_jobs_bulk(jobs)
        return json.dumps({
            "status": "success",
            "jobs_found": len(jobs),
            "new_jobs_saved": count,
            "source": "Internshala",
            "sample_jobs": jobs[:5]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_unmatched_jobs() -> str:
    """
    Get all scraped jobs that haven't been matched against the resume yet.
    Use this to find jobs that need to be evaluated for suitability.

    Returns:
        JSON string with unprocessed job listings
    """
    jobs = db.get_unprocessed_jobs()
    return json.dumps({
        "count": len(jobs),
        "jobs": jobs[:20]  # Limit to avoid token overflow
    }, indent=2, default=str)


@tool
def get_resume_text() -> str:
    """
    Get the currently uploaded resume text and extracted skills.
    Use this when you need to compare the resume against job requirements.

    Returns:
        JSON string with resume text and skills
    """
    resume = db.get_active_resume()
    if not resume:
        return json.dumps({
            "status": "error",
            "message": "No resume uploaded. Please upload a resume first."
        })
    return json.dumps({
        "status": "success",
        "file_name": resume["file_name"],
        "skills": resume["skills"],
        "text_preview": resume["raw_text"][:3000]  # Limit tokens
    }, indent=2)


@tool
def save_match_result(job_id: int, match_score: float, match_reasons: str,
                      decision: str, decision_reasoning: str) -> str:
    """
    Save the result of matching a job against the resume.
    Use this after evaluating how well a job fits the candidate.

    Args:
        job_id: The ID of the job being evaluated
        match_score: Score from 0.0 to 1.0 indicating match quality
        match_reasons: Explanation of why this job matches or doesn't
        decision: One of 'apply', 'skip', or 'review' - the recommended action
        decision_reasoning: Detailed reasoning for the decision

    Returns:
        Confirmation message
    """
    try:
        status_map = {
            "apply": "recommended",
            "skip": "skipped",
            "review": "review"
        }
        app_data = {
            "job_id": job_id,
            "match_score": match_score,
            "match_reasons": match_reasons,
            "status": status_map.get(decision, "review"),
            "decision_reasoning": decision_reasoning
        }
        app_id = db.add_application(app_data)
        return json.dumps({
            "status": "success",
            "application_id": app_id,
            "decision": decision,
            "match_score": match_score
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def generate_cover_letter(job_id: int, tone: str = "professional") -> str:
    """
    Generate a tailored cover letter for a specific job based on the resume.
    Use this after deciding to apply to a job.

    Args:
        job_id: The ID of the job to generate a cover letter for
        tone: Desired tone - 'professional', 'enthusiastic', or 'concise'

    Returns:
        The generated cover letter text
    """
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate

    job = db.get_job_by_id(job_id)
    resume = db.get_active_resume()

    if not job:
        return json.dumps({"status": "error", "message": f"Job {job_id} not found"})
    if not resume:
        return json.dumps({"status": "error", "message": "No resume uploaded"})

    llm = ChatOpenAI(
        model=Config.OPENAI_MODEL,
        temperature=0.7,
        api_key=Config.OPENAI_API_KEY
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert career coach who writes compelling, 
         personalized cover letters. Write cover letters that:
         - Are tailored to the specific job and company
         - Highlight relevant experience from the resume
         - Show genuine enthusiasm for the role
         - Are concise (250-350 words)
         - Use a {tone} tone
         - Include specific examples from the candidate's experience
         - Are formatted as a proper business letter"""),
        ("human", """Write a cover letter for the following:

**Job Title:** {title}
**Company:** {company}
**Location:** {location}
**Job Description:** {description}
**Requirements:** {requirements}

**Candidate's Resume:**
{resume_text}

**Candidate's Key Skills:** {skills}

Generate a compelling, personalized cover letter.""")
    ])

    chain = prompt | llm
    response = chain.invoke({
        "tone": tone,
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "description": job.get("description", "")[:2000],
        "requirements": job.get("requirements", "")[:1000],
        "resume_text": resume["raw_text"][:3000],
        "skills": ", ".join(resume["skills"]),
    })

    cover_letter = response.content

    # Save cover letter to file
    Config.ensure_dirs()
    safe_company = "".join(c if c.isalnum() else "_" for c in job.get("company", "unknown"))
    filename = f"cover_letter_{safe_company}_{job_id}_{datetime.now().strftime('%Y%m%d')}.txt"
    filepath = os.path.join(Config.COVER_LETTERS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(cover_letter)

    # Update application record
    apps = db.get_applications()
    for app in apps:
        if app["job_id"] == job_id:
            db.update_application(app["id"], {
                "cover_letter": cover_letter,
                "cover_letter_path": filepath,
                "status": "cover_letter_ready"
            })
            break

    return json.dumps({
        "status": "success",
        "cover_letter": cover_letter,
        "saved_to": filepath
    }, indent=2)


@tool
def get_application_stats() -> str:
    """
    Get statistics about all job applications.
    Use this to provide the user with an overview of their application pipeline.

    Returns:
        JSON string with application statistics
    """
    stats = db.get_stats()
    return json.dumps(stats, indent=2, default=str)


@tool
def update_application_status(application_id: int, new_status: str, notes: str = "") -> str:
    """
    Update the status of a job application.
    Use this to track application progress.

    Args:
        application_id: The ID of the application to update
        new_status: New status (e.g. 'applied', 'interview', 'rejected', 'offered')
        notes: Optional notes about the status change

    Returns:
        Confirmation message
    """
    try:
        updates = {"status": new_status}
        if notes:
            updates["notes"] = notes
        if new_status == "applied":
            updates["applied_at"] = datetime.now().isoformat()

        db.update_application(application_id, updates)
        return json.dumps({
            "status": "success",
            "message": f"Application {application_id} updated to '{new_status}'"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_all_tools() -> list:
    """Return all available agent tools."""
    return [
        scrape_linkedin_jobs,
        scrape_internshala_jobs,
        get_unmatched_jobs,
        get_resume_text,
        save_match_result,
        generate_cover_letter,
        get_application_stats,
        update_application_status,
    ]
