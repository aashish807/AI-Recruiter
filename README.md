# AI Recruiter

**Next-Generation Autonomous Talent Acquisition & Ranking System**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://python.langchain.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org/)

---

## Overview

**AI Recruiter** is an end-to-end intelligent platform that automates the recruitment pipeline. By leveraging the power of Large Language Models (LLMs), LangChain, LangGraph, and Vector Databases (FAISS), it parses resumes, extracts key skills, matches candidates to job descriptions, and intelligently ranks them.

Built for scale and speed, this project is perfect for HR teams wanting to cut down resume screening time by 90% and identify top talent with AI-driven explainability.

## Key Features

-  **Omni-Format Resume Parsing**: Seamlessly extract text from PDFs, DOCX, and Excel files.
-  **Intelligent Candidate Ranking**: Uses LLMs and vector embeddings to match candidate profiles against job requirements semantically.
-  **Explainable AI (XAI)**: Provides clear, generated reasoning on *why* a candidate was ranked highly and what their skill gaps might be.
-  **Interactive Dashboard**: A sleek React-based UI to view candidate profiles, manage job descriptions, and review AI reports.
-  **Containerized Architecture**: Fully Dockerized for a "one-click" setup experience.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI/ML**: LangChain, LangGraph, OpenAI GPT, FAISS (Vector DB), Sentence Transformers
- **Database & ORM**: PostgreSQL, SQLAlchemy, SQLite (fallback/local DB support)
- **Document Processing**: PyPDF, python-docx, pandas, openpyxl

### Frontend
- **Framework**: React.js (via Vite)
- **PDF Viewing**: pdfjs-dist

### Infrastructure
- **Deployment**: Docker, Docker Compose

## Architecture

1. **Ingestion**: Resumes are uploaded via the React frontend to the FastAPI backend.
2. **Processing & Extraction**: Documents are parsed, chunked, and embedded into the FAISS vector database.
3. **Analysis Engine**: LangChain agents evaluate the embeddings against the active Job Description (JD).
4. **Scoring & Reporting**: The AI generates a score and an explainability report, saving the structured results into PostgreSQL.
5. **Presentation**: The frontend fetches and displays the ranked list of candidates along with detailed AI insights.

---

##  Getting Started

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/get-started)
- [Node.js](https://nodejs.org/) (if running frontend locally outside Docker)
- [Python 3.9+](https://www.python.org/) (if running backend locally outside Docker)
- An [OpenAI API Key](https://platform.openai.com/api-keys)

### Environment Setup

Create a `.env` file in the root of the project and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

###  Quick Start (Recommended - Docker)

The easiest way to get the app running is via Docker Compose, which will spin up the Postgres database, FastAPI backend, and React frontend simultaneously.

```bash
# Build and start all services in detached mode
docker-compose up --build -d
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database**: Port `5432`

To stop the services:
```bash
docker-compose down
```

### Local Setup (Without Docker)

If you prefer to run the services locally for development:

#### 1. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Future Roadmap (Hackathon Ready)

- [ ] **Automated Interview Outreach**: Integrate with email APIs (SendGrid/Nylas) to automatically email top candidates.
- [ ] **Video Interview Analysis**: Incorporate speech-to-text to analyze candidate video pitches.
- [ ] **Bias Mitigation Module**: Introduce a dedicated agent to strip PII (Personally Identifiable Information) before evaluation to ensure unbiased ranking.
- [ ] **Multi-Agent Negotiations**: Implement AI agents that can simulate salary negotiations based on candidate skills and market data.

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](#).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
# AI-Recruiter
