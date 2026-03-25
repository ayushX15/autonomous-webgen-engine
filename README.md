# Autonomous WebGen Engine

Agentic website design generation system that transforms user requirements 
and reference sites into deployable Next.js 14 websites using AI.

## Architecture
- **Agentic Framework:** LangGraph (iterative feedback loop)
- **LLM:** Gemini 2.5 Flash (text + vision)
- **Visual Review:** Playwright headless browser
- **Backend:** FastAPI (Python 3.10)
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS

## Setup

### 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/autonomous-webgen-engine.git
cd autonomous-webgen-engine

### 2. Create Python virtual environment
python -m venv ai_env
# Windows:
ai_env\Scripts\Activate.ps1
# Mac/Linux:
source ai_env/bin/activate

### 3. Install Python dependencies
cd ai-design-agent
pip install -r backend/requirements.txt

### 4. Install Playwright browsers
playwright install chromium

### 5. Create secret.env
Create ai-design-agent/secret.env:
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
SIMILARITY_THRESHOLD=0.75
MAX_ITERATIONS=3
GENERATED_OUTPUT_DIR=./generated-output

Get your free Gemini API key at: https://aistudio.google.com

### 6. Install frontend dependencies
cd control-panel
npm install

## Running

Terminal 1 — Backend:
cd ai-design-agent
python -m uvicorn backend.main:app --reload --port 8000

Terminal 2 — Frontend:
cd ai-design-agent/control-panel
npm run dev

Terminal 3 — Generated Final Output
copy the location from the frontend and paste in the terminal 3
npm run dev

Open: http://localhost:3000