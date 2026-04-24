"""
Flask Web Dashboard – Routes and API endpoints for the AI Job Application Agent.
Provides a rich web interface for managing the entire job application pipeline.
"""

import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

from config import Config
from database.models import Database
from utils.resume_parser import parse_resume
from agent.agent import JobApplicationAgent

logger = logging.getLogger(__name__)

# ── Flask App Setup ──────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.secret_key = Config.FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

db = Database()
agent = None  # Lazy-initialized


def get_agent():
    """Lazy-initialize the agent (requires API key)."""
    global agent
    if agent is None:
        try:
            agent = JobApplicationAgent()
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return None
    return agent


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Page Routes ──────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Main dashboard with overview statistics."""
    stats = db.get_stats()
    recent_apps = db.get_applications(limit=5)
    resume = db.get_active_resume()
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_apps=recent_apps,
        resume=resume,
        page="dashboard"
    )


@app.route("/jobs")
def jobs_list():
    """View all scraped jobs."""
    source = request.args.get("source", None)
    page_num = int(request.args.get("page", 1))
    per_page = 20
    offset = (page_num - 1) * per_page

    jobs = db.get_jobs(source=source, limit=per_page, offset=offset)
    total = db.get_job_count(source=source)
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "jobs.html",
        jobs=jobs,
        source=source,
        page_num=page_num,
        total_pages=total_pages,
        total=total,
        page="jobs"
    )


@app.route("/applications")
def applications_list():
    """View all applications with filtering."""
    status = request.args.get("status", None)
    min_score = request.args.get("min_score", None)

    if min_score:
        min_score = float(min_score)

    apps = db.get_applications(status=status, min_score=min_score)
    return render_template(
        "applications.html",
        applications=apps,
        current_status=status,
        min_score=min_score,
        page="applications"
    )


@app.route("/application/<int:app_id>")
def application_detail(app_id):
    """View detailed application info including cover letter."""
    app_data = db.get_application_by_id(app_id)
    if not app_data:
        flash("Application not found", "error")
        return redirect(url_for("applications_list"))
    return render_template(
        "application_detail.html",
        app=app_data,
        page="applications"
    )


@app.route("/resume")
def resume_page():
    """Resume upload and management page."""
    resume = db.get_active_resume()
    return render_template("resume.html", resume=resume, page="resume")


@app.route("/chat")
def chat_page():
    """Interactive chat with the AI agent."""
    return render_template("chat.html", page="chat")


# ── API Endpoints ────────────────────────────────────────────────────

@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    """Handle resume file upload."""
    if "resume" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PDF, DOCX, or TXT"}), 400

    Config.ensure_dirs()
    filename = secure_filename(file.filename)
    filepath = os.path.join(Config.UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        parsed = parse_resume(filepath)
        db.save_resume(
            file_name=filename,
            file_path=filepath,
            raw_text=parsed["raw_text"],
            skills=parsed["skills"]
        )
        return jsonify({
            "status": "success",
            "file_name": filename,
            "skills_found": parsed["skills"],
            "text_length": len(parsed["raw_text"])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])
def scrape_jobs():
    """Trigger job scraping from specified sources."""
    data = request.get_json()
    query = data.get("query", "")
    location = data.get("location", "India")
    sources = data.get("sources", ["linkedin", "internshala"])

    if not query:
        return jsonify({"error": "Search query is required"}), 400

    results = {}

    if "linkedin" in sources:
        try:
            from scraper.linkedin_scraper import LinkedInScraper
            scraper = LinkedInScraper()
            jobs = scraper.scrape_jobs(query, location)
            count = db.add_jobs_bulk(jobs)
            results["linkedin"] = {"found": len(jobs), "new": count}
        except Exception as e:
            results["linkedin"] = {"error": str(e)}

    if "internshala" in sources:
        try:
            from scraper.internshala_scraper import InternShalaScraper
            scraper = InternShalaScraper()
            jobs = scraper.scrape_jobs(query, location)
            count = db.add_jobs_bulk(jobs)
            results["internshala"] = {"found": len(jobs), "new": count}
        except Exception as e:
            results["internshala"] = {"error": str(e)}

    return jsonify({"status": "success", "results": results})


@app.route("/api/chat", methods=["POST"])
def chat_with_agent():
    """Send a message to the AI agent and get a response."""
    data = request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    ai_agent = get_agent()
    if not ai_agent:
        return jsonify({
            "error": "Agent not available. Check your OPENAI_API_KEY in .env"
        }), 500

    result = ai_agent.run(message)
    return jsonify(result)


@app.route("/api/quick-match", methods=["POST"])
def quick_match():
    """Run the full matching pipeline."""
    ai_agent = get_agent()
    if not ai_agent:
        return jsonify({"error": "Agent not available"}), 500

    result = ai_agent.quick_match()
    return jsonify(result)


@app.route("/api/scrape-and-match", methods=["POST"])
def scrape_and_match():
    """Full pipeline: scrape → match → generate cover letters."""
    data = request.get_json()
    query = data.get("query", "")
    location = data.get("location", "India")
    sources = data.get("sources", ["linkedin", "internshala"])

    if not query:
        return jsonify({"error": "Search query is required"}), 400

    ai_agent = get_agent()
    if not ai_agent:
        return jsonify({"error": "Agent not available"}), 500

    result = ai_agent.scrape_and_match(query, sources, location)
    return jsonify(result)


@app.route("/api/application/<int:app_id>/status", methods=["PUT"])
def update_status(app_id):
    """Update an application's status."""
    data = request.get_json()
    new_status = data.get("status", "")
    notes = data.get("notes", "")

    if not new_status:
        return jsonify({"error": "Status is required"}), 400

    try:
        db.update_application(app_id, {
            "status": new_status,
            "notes": notes
        })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """Get dashboard statistics as JSON."""
    stats = db.get_stats()
    return jsonify(stats)


@app.route("/api/generate-cover-letter/<int:job_id>", methods=["POST"])
def generate_cover_letter_api(job_id):
    """Generate a cover letter for a specific job."""
    data = request.get_json() or {}
    tone = data.get("tone", "professional")

    ai_agent = get_agent()
    if not ai_agent:
        return jsonify({"error": "Agent not available"}), 500

    result = ai_agent.run(
        f"Generate a {tone} cover letter for job ID {job_id}"
    )
    return jsonify(result)
