# AutoApply — AI-Powered Job Application Engine

> **100+ tailored applications per day. Fully automated. Open source.**

AutoApply is a 5-layer job application system that discovers jobs, tailors your resume using local AI (Llama3), generates professional documents, and auto-applies to career pages — all while learning what works over time.

Built by [Atharva Vaidya](https://linkedin.com/in/atharvav) as an open-source tool for job seekers everywhere.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Netlify (free)  — React Dashboard               │
│  Profile Setup │ Job Queue │ Applications │ Analytics        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│          DigitalOcean Droplet ($12/mo, $200 credit)          │
│                                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────────────┐  │
│  │Discovery│→ │Intelligence│→│Document│  │   SQLite DB   │  │
│  │ Engine  │  │  Engine   │  │Factory │  │ Full history   │  │
│  └─────────┘  └──────────┘  └────────┘  └───────────────┘  │
│   Playwright   Groq API      python-docx  Dedup + tracking  │
│   Scraping     Llama3-70B    .docx gen    A/B test data     │
│   3 boards     FREE tier     Templates                      │
└─────────────────────────────────────────────────────────────┘
                           │ Job queue + resumes
┌──────────────────────────┴──────────────────────────────────┐
│            Your Local Machine (CLI script)                    │
│                                                              │
│  ┌─────────┐  ┌──────────┐                                  │
│  │  RPA    │→ │ Learning │  Your real IP, real cookies       │
│  │ Apply   │  │  Loop    │  No cloud detection               │
│  └─────────┘  └──────────┘  5 ATS adapters                   │
│   Playwright   Outcomes      Workday, Greenhouse, Lever,     │
│   Auto-fill    A/B track     iCIMS, Taleo                    │
└─────────────────────────────────────────────────────────────┘
```

## 5 Layers

### Layer 1: Discovery Engine
- Scrapes LinkedIn, Indeed, Glassdoor, BuiltIn via Selenium + BeautifulSoup
- Configurable search queries, location, recency filters
- Deduplicates against full application history (never applies twice)
- Runs on schedule (2x daily via APScheduler)

### Layer 2: Intelligence Engine
- Runs Llama3 locally via Ollama (free, private, no API costs)
- Generates archetype playbook (groups similar jobs, writes rewrite rules)
- Tailors resume bullets per job using your voice rules and proof points
- Mirrors employer language using JD phrase extraction

### Layer 3: Document Factory
- Generates .docx resumes from your template (python-docx)
- Produces cover letters matching your voice signature
- Outputs are pixel-perfect to your formatting spec

### Layer 4: RPA Applicant
- Browser automation via Playwright (headless or visible)
- 5 ATS-specific adapters: Workday, Greenhouse, Lever, iCIMS, Taleo
- Auto-fills standard fields (name, email, education, work history)
- Uploads tailored resume + cover letter
- Skips custom questions, flags for manual review
- Screenshot capture for verification

### Layer 5: Learning Loop
- Tracks every application: submitted → viewed → callback → interview → offer/reject
- A/B tests resume framings (which archetype works best for which company type)
- Builds local fine-tuning dataset from successful applications
- Feeds winning patterns back into Layer 2 prompts

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free — runs Llama3-70B at 500+ tok/sec)
- Chrome/Chromium (for Playwright scrapers)
- Optional: [Ollama](https://ollama.ai) for fully offline LLM usage

### Setup (Local Development)

```bash
# Clone
git clone https://github.com/yourusername/autoapply.git
cd autoapply

# Backend
pip install -r requirements.txt
playwright install chromium

# Get your free Groq API key at console.groq.com
cp .env.example .env
# Edit .env: add GROQ_API_KEY=gsk_your_key_here

# Frontend
cd frontend && npm install && cd ..

# Run
cd backend && uvicorn main:app --reload  # API on :8000
cd frontend && npm run dev               # UI on :5173
```

### Production Deployment

**Frontend → Netlify (free)**
```bash
# Connect GitHub repo to Netlify
# Build command: npm run build
# Publish directory: dist
# Update netlify.toml with your backend URL
```

**Backend → DigitalOcean ($12/mo, $200 credit with GitHub Student Pack)**
```bash
# Create Basic Droplet: 2GB RAM, 1 vCPU, Ubuntu 24.04
scp deploy/setup-droplet.sh root@YOUR_IP:~
ssh root@YOUR_IP 'bash setup-droplet.sh'
```

**RPA → Your Local Machine**
```bash
# Auto-apply using your real browser (avoids detection)
python rpa_local.py --server https://your-api.com --limit 10
python rpa_local.py --server https://your-api.com --limit 10 --dry-run  # test first
```

### First Run
1. Open http://localhost:5173
2. Complete your profile setup (resume, target roles, voice rules)
3. Configure search queries for your target roles
4. Click "Run Discovery" to find jobs
5. Review the job queue, click "Generate Playbook"
6. Click "Tailor All" to generate custom resumes
7. Click "Auto-Apply" to submit applications

## Configuration

Edit `.env` or use the dashboard:

```env
# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Discovery
SEARCH_QUERIES=Strategy Operations Analyst,Business Transformation Consultant
TARGET_LOCATIONS=United States,Remote
MAX_JOBS_PER_CYCLE=10
CYCLES_PER_RUN=10

# RPA
HEADLESS_BROWSER=true
SCREENSHOT_ON_APPLY=true
SKIP_CUSTOM_QUESTIONS=true

# Schedule
RUN_SCHEDULE=08:00,18:00
```

## Project Structure

```
autoapply/
├── backend/
│   ├── main.py                 # FastAPI app + routes
│   ├── config.py               # Settings management
│   ├── database.py             # SQLite models + ORM
│   ├── scheduler.py            # APScheduler for 2x daily runs
│   ├── discovery/
│   │   ├── scraper_base.py     # Base scraper class
│   │   ├── linkedin.py         # LinkedIn scraper
│   │   ├── indeed.py           # Indeed scraper
│   │   ├── glassdoor.py        # Glassdoor scraper
│   │   └── dedup.py            # Deduplication engine
│   ├── intelligence/
│   │   ├── llama_client.py     # Ollama API wrapper
│   │   ├── playbook.py         # Archetype playbook generator
│   │   ├── tailor.py           # Resume tailoring engine
│   │   ├── content_os.py       # Voice rules + writing system
│   │   └── prompts.py          # All LLM prompts
│   ├── documents/
│   │   ├── resume_gen.py       # .docx resume generator
│   │   └── cover_letter_gen.py # Cover letter generator
│   ├── rpa/
│   │   ├── applicant.py        # Base applicant + orchestrator
│   │   └── adapters/
│   │       ├── workday.py
│   │       ├── greenhouse.py
│   │       ├── lever.py
│   │       ├── icims.py
│   │       └── taleo.py
│   └── learning/
│       ├── tracker.py          # Outcome tracking
│       ├── ab_test.py          # A/B test engine
│       └── feedback.py         # Fine-tuning data builder
├── frontend/
│   └── src/
│       ├── App.jsx             # Main dashboard
│       ├── pages/
│       │   ├── Dashboard.jsx   # Overview + stats
│       │   ├── Profile.jsx     # Profile setup
│       │   ├── Jobs.jsx        # Job queue + review
│       │   └── Analytics.jsx   # Learning loop stats
│       └── utils/
│           └── api.js          # Backend API client
├── data/
│   ├── profiles/               # User profile JSON files
│   ├── outputs/                # Generated resumes + cover letters
│   └── autoapply.db            # SQLite database
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

## License

License TBD. Built to be flexible for both open-source and commercial use.

## Contributing

PRs welcome. See CONTRIBUTING.md for guidelines.

---

*Built with frustration at applying to 100+ jobs manually. Now the machines do it.*
