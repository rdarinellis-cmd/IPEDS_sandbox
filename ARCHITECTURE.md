IPEDS Dashboard: Project Status & Architecture Blueprint
📜 1. Context & Scope
Target Audience: Higher education data consumers looking for fast, intuitive, multi-page web dashboards to explore the last 5 years of National Center for Education Statistics (NCES) IPEDS institutional data.
Developer Mindset: Re-engaging with coding after a multi-decade hiatus (BASIC/FORTRAN backgrounds). Value simplicity, lean toolsets, standard libraries, and zero-to-low cost footprint.
Primary Constraints: Avoid heavy database infrastructure or complex cloud authentication overhead in application code.
🏗️ 2. Architectural Evolution
We refactored the data pipeline away from an overly complex distributed architecture to a high-speed, local-memory, file-based model:
Attribute	Old Architecture (Legacy)	New Architecture (Current)
Data Engine	Google BigQuery (Client-Server SQL)	In-Memory Pandas + Apache Parquet
Dictionary Setup	Stored remotely in BigQuery	Local .xlsx NCES lookups in /dictionaries
Auth Complexity	Strict JSON Service Account Keys	Zero Application-level authentication
Compute Profile	External Cloud Data Warehousing	Fast, local multi-threaded file execution
Hosting Strategy	Streamlit Cloud / Hugging Face Spaces	Google Cloud Run (Stateless Container)
📁 3. Workspace Layout
Plaintext
IPEDS_sandbox/
├── .venv/                  # Hidden: Isolated local Python packages (Never push to Git)
├── .gitignore              # Controls what files are blocked from GitHub
├── ARCHITECTURE.md         # This document (Operational Reference)
├── app.py                  # Streamlit entry point & Page 1 (Main UI Layout)
├── download_data.py        # Automated GCloud-to-Local conversion script
├── requirements.txt        # Container package list with safe minimum pinning (>=)
├── Dockerfile              # Cloud Run container blueprint recipe
├── data/                   # Cached local data tables (*.parquet)
└── dictionaries/           # Variable definition translation tables (*.xlsx)
🛠️ 4. Operational Playbooks (zsh Terminal)
A. Taming the Virtual Environment (Local Run)
Execute this sequence every time you open a brand new terminal window to work on your Mac:
Bash
# 1. Navigate to the project root
cd ~/Antigravity/IPEDS_sandbox

# 2. Wake up your isolated environment
source .venv/bin/activate

# 3. Boot your dashboard locally
streamlit run app.py
B. Shipping Code to the Vault (GitHub Sync)
Our primary version control pipeline across both your work machine (ac7940) and home machine (darinellis):
Bash
git status
git add .
git commit -m "Describe your modifications clearly"
git push origin main
C. Deploying to Production (Google Cloud Run)
Deploys the app as a stateless container, running inside a strict financial safety profile:
Bash
gcloud run deploy ipeds-dashboard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 2
🔒 5. Financial Safety Railings
To prevent runaway billing and ensure we remain inside a near-zero cost profile ($0.00 to $1.00/month), the following infrastructure safety caps have been locked into your active Google Cloud Account (project-9a1f71b9-7c50-4df5-adb):
Concurrency Ceiling: Capped at --max-instances 2 on Cloud Run. The cloud will never spin up a third server image, naturally blocking high-traffic billing surges.
Escalating Budget Alerts: An automated zsh budget script linked to your main billing ID triggers notification warnings to your verified email address at 50% ($2.50), 90% ($4.50), and 100% ($5.00) of your strict monthly threshold.
🗺️ 6. Future Project Roadmap
Phase 1: Interactive Data Lookups (Current Goal)
Integrate the /dictionaries logic dynamically inside app.py.
Wire up human-readable dropdown labels so users see "Public, 4-year" instead of selecting CONTROL = 1.
Phase 2: Performance Tuning (Optional Upgrade Flags)
DuckDB Integration: If cross-table joins become sluggish inside standard Pandas dataframes, we will drop DuckDB directly into requirements.txt. It executes localized serverless SQL queries straight inside your app's RAM without needing external cloud databases.
Phase 3: The Hard Kill Switch (Advanced Infrastructure)
If automated email notifications feel too reactive, we can construct an explicit automated sever line. This requires piping your budget alerts into a Google Cloud Pub/Sub Topic that fires a custom Cloud Function script to programmatically disconnect billing links the exact second a budget limit is reached.
🤖 7. Context Anchor for Antigravity Chat
Whenever you start a brand new chat tab in your IDE, paste this paragraph to immediately ground the AI agent in this reality without wasting time repeating your background:
"We are working on the IPEDS Streamlit dashboard project located in this workspace root. Our architecture relies on local caching via compressed .parquet tables and Excel lookup files inside /dictionaries. The application deploys to Google Cloud Run using a custom Dockerfile with strict budget parameters and a serverless configuration. Please read the ARCHITECTURE.md file in this directory to align your code generation scripts, terminal selections, and prompt styles with our existing blueprint rules."