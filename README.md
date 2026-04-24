# 🤖 AI Job Application Agent

An intelligent, agentic AI system that automates the job application pipeline — from discovering opportunities to crafting perfect cover letters.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![LangChain](https://img.shields.io/badge/LangChain-Agents-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange)
![Selenium](https://img.shields.io/badge/Selenium-Scraping-yellow)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Job Scraping** | Automated scraping from LinkedIn & Internshala using Selenium |
| 🎯 **AI Matching** | LLM-powered resume matching with scored recommendations |
| ✉️ **Cover Letters** | Tailored cover letter generation for each position |
| 📊 **Tracking** | Full application pipeline tracking with status management |
| 🤖 **Agentic AI** | LangChain agent that decides which jobs to apply to |
| 💬 **AI Chat** | Interactive chat with the agent for custom queries |
| 🌐 **Web Dashboard** | Beautiful dark-mode dashboard with glassmorphism design |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                Web Dashboard (Flask)                │
│  Resume Upload │ Job Feed │ Applications │ AI Chat  │
└──────────┬──────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────┐
│            LangChain Agent Orchestrator              │
│  ┌────────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Job Scraper│ │ Resume   │ │ Cover Letter     │   │
│  │   Tool     │ │ Matcher  │ │ Generator        │   │
│  └────────────┘ └──────────┘ └──────────────────┘   │
│  ┌────────────┐ ┌──────────┐                        │
│  │ Application│ │ Decision │                        │
│  │ Tracker    │ │ Engine   │                        │
│  └────────────┘ └──────────┘                        │
└──────────┬──────────────────────────────────────────┘
           │
┌──────────▼───────────┐  ┌──────────────────┐
│   SQLite Database    │  │    OpenAI API    │
│  (Applications DB)   │  │   (GPT-4o-mini) │
└──────────────────────┘  └──────────────────┘
```

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd ai_job
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

## 📖 Usage

### Web Dashboard
1. **Upload Resume** → Go to Resume page and upload your PDF/DOCX
2. **Scrape Jobs** → Use the dashboard to search LinkedIn/Internshala
3. **AI Match** → Click "AI Quick Match" to evaluate jobs against your resume
4. **Cover Letters** → Auto-generated for high-scoring matches
5. **Track** → Update application statuses as you progress

### AI Chat
Chat naturally with the agent:
- *"Find me Python developer jobs in Bangalore"*
- *"Which jobs should I apply to?"*
- *"Generate a cover letter for the Google position"*
- *"Show me my application statistics"*

### Full Pipeline (One Click)
Use **"Full AI Pipeline"** from the dashboard to automatically:
1. Scrape new jobs
2. Match against your resume
3. Score and rank opportunities
4. Generate cover letters for top matches

## 🧠 How the Agent Decides

The AI agent uses a weighted scoring framework:

| Factor | Weight | Description |
|--------|--------|-------------|
| Skills Match | 40% | Required skills vs. resume skills |
| Experience Alignment | 25% | Experience level compatibility |
| Role Relevance | 20% | Job title to career goals alignment |
| Growth Potential | 15% | Learning and advancement opportunities |

**Decision thresholds:**
- ≥ 70% → **APPLY** (strong match)
- 40-70% → **REVIEW** (flag for manual review)
- < 40% → **SKIP** (poor match)

## 📁 Project Structure

```
ai_job/
├── app.py                 # Main entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
│
├── agent/                 # LangChain AI Agent
│   ├── agent.py           # Agent orchestrator
│   └── tools.py           # Agent tools (scrape, match, etc.)
│
├── scraper/               # Job scrapers
│   ├── base_scraper.py    # Base Selenium scraper
│   ├── linkedin_scraper.py
│   └── internshala_scraper.py
│
├── database/              # SQLite database layer
│   └── models.py          # DB models & queries
│
├── utils/                 # Utilities
│   └── resume_parser.py   # PDF/DOCX resume parser
│
├── web/                   # Flask web dashboard
│   ├── app.py             # Routes & API endpoints
│   ├── static/
│   │   ├── css/style.css  # Design system
│   │   └── js/app.js      # Frontend logic
│   └── templates/         # Jinja2 templates
│       ├── base.html
│       ├── dashboard.html
│       ├── jobs.html
│       ├── applications.html
│       ├── application_detail.html
│       ├── resume.html
│       └── chat.html
│
└── uploads/               # Resume uploads
```

## 🔧 Tech Stack

- **Python 3.10+** – Core language
- **LangChain** – Agent framework with tool-use
- **OpenAI GPT-4o-mini** – Matching, cover letters, decisions
- **Selenium** – Browser automation for scraping
- **BeautifulSoup4** – HTML parsing
- **Flask** – Web dashboard backend
- **SQLite** – Application tracking database
- **PyPDF2 / python-docx** – Resume parsing

## ⚠️ Important Notes

- **API Key**: You need an OpenAI API key. Set it in `.env`.
- **Scraping**: LinkedIn may rate-limit or block automated access. Use responsibly.
- **Headless Mode**: Scraping runs headless by default. Set `HEADLESS_BROWSER=false` in `.env` to see the browser.
- **Chrome Required**: Selenium requires Chrome/Chromium. The `webdriver-manager` package handles driver installation automatically.

## 📜 License

MIT License – use freely for personal job searching.
