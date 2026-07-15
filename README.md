# QuestTube AI - YouTube Research Assistant

QuestTube AI is a premium, full-stack AI-powered YouTube Research Assistant built with Python, Django, SQLite, and vanilla frontend technologies. It transforms public YouTube video transcripts and playlists into an AI knowledge base, letting users conduct multi-video comparative studies, dialogue-driven research, side-by-side analysis, conflict detection, study material generation, and token usage analytics.

---

## 🌟 Key Features

* **Multi-Video & Playlist Ingestion**: Submitting a single video URL or an entire YouTube playlist processes all relevant videos, pulls transcripts asynchronously, chunks text blocks, and fetches metadata.
* **Semantic Vector Search (RAG)**: Processes and queries transcripts using a SQLite vector database with custom NumPy-based cosine similarity search to retrieve contextual snippets.
* **Dialogue QA with Citation Seeking**: Ask the AI chatbot questions across selected transcripts. The response embeds citation tags that let you seek directly to the exact timestamp in the integrated YouTube player.
* **Research Workspace**:
  * **Side-by-Side Comparison**: Compares multiple video contents based on a specified topic.
  * **Contradiction Detection**: Flags claims that disagree or contradict each other across different videos.
  * **Structured Markdown Reports**: Generates formal, detailed markdown reports summarizing key themes, analyses, and source evidence.
* **Learning & Study Hub**:
  * **Summaries**: Generates short, detailed, or bulleted summaries.
  * **Interactive Quizzes**: Generates JSON multiple-choice questions with real-time scoring.
  * **Flipping Study Flashcards**: Beautifully styled 3D flipping cards mapping terms and explanations.
  * **Detailed Study Guides**: Compiles structured study guide notes in markdown.
* **Usage & Analytics**: Live tracking of total API calls, token counts, and cost allocations rendered as interactive SVG charts.
* **Secure JWT Authentication**: Account creation and login secured with JWT access and refresh tokens.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.13, Django 6.0, Django REST Framework, SQLite
* **Mathematics**: NumPy (vector cosine similarity calculation)
* **AI Providers**: Gemini API (`google-genai` SDK), OpenAI API
* **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism Dark-Mode), Vanilla JavaScript
* **Authentication**: Django REST Framework Simple-JWT
* **Background Tasks**: Python `ThreadPoolExecutor` (asynchronous scrape & embed queues)

---

## 📂 Project Structure

```text
config/                  # Main settings & routing
  settings.py            # App registry, JWT setup, AI credentials
  services/              # Service Factory & AI Provider wrappers
    providers.py         # Abstract interfaces for LLM/Embeddings
    gemini.py            # Gemini Client (gemini-3.1-flash-lite)
    openai.py            # OpenAI Client (gpt-4o-mini)
    background_utils.py  # Thread pool background worker
accounts/                # User signup, profile, and JWT auth views
videos/                  # YouTube URL & playlist ingestion pipelines
transcripts/             # Subscript extraction & overlap text chunking
knowledge_base/          # SQLite vector database semantic search
ai_chat/                 # Chat log database & dialogue QA views
research/                # Cross-video comparison & markdown report views
learning/                # Summary, quiz, note, and flashcard generators
analytics/               # Token analytics logging models & summary API
templates/index.html     # Single Page Application main dashboard
static/                  # Custom CSS (style.css) & Client JS (app.js)
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
Ensure you have Python 3.10+ and Git installed on your system.

### 2. Clone and Activate Environment
```bash
git clone https://github.com/Lokesh8039/QuestTube-AI.git
cd QuestTube-AI

# Create virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate
# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```ini
# Django Config
SECRET_KEY=your-secure-django-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Config (Choose: gemini or openai)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Apply Migrations & Seed Admin User
```bash
# Apply SQLite database migrations
python manage.py migrate

# Create test admin user account (optional, you can also signup on the web)
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```
Visit **`http://127.0.0.1:8000/`** to log in, register, and start researching!

---

## 🧪 Running Automated Tests
The suite includes Django unit tests covering user auth, transcript scraping, sentence overlaps, and NumPy cosine similarity scoring:
```bash
python manage.py test
```
