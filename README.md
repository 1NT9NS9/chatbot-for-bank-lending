# Chatbot for Bank Lending – Mini-MVP

This repository contains a minimal viable product of a Retrieval-Augmented-Generation (RAG) chatbot that answers questions about lending conditions (in Russian).  
It is built with FastAPI, Postgres + pgvector and Gemini LLM.

## Contents
1. Quick start with Docker Compose  
2. Environment variables  
3. API reference & Swagger-UI  
4. Example cURL request  
5. Development workflow  
6. Running the ETL job manually  
7. Testing & QA  

## Project architecture

   ![image](https://github.com/user-attachments/assets/129f7f8e-8c2a-45eb-ab03-537ebf31d0ac)
   
---

## 1. Quick start

### Prerequisites
- Docker Desktop installed
- Python >= 3.10 (for local development)
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Setup
```powershell
# clone the repo
git clone https://github.com/1NT9NS9/chatbot-for-bank-lending.git
cd chatbot-for-bank-lending

# copy env example and set your API key
cp env.example .env
# Edit .env file and add your GEMINI_API_KEY

# build & run all services
docker compose up --build -d

# view logs (optional)
docker compose logs -f chat-service
```
The stack exposes:
* Chat-service (FastAPI) – http://localhost:8000  
* Prometheus metrics – http://localhost:8000/metrics  
* Postgres – localhost:5432 (user/pass: `chat`)

When finished:
```powershell
docker compose down -v   # stop & remove volumes
```

## 2. Environment variables
| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **Required.** API-key for Google Gemini. |
| `DATABASE_URL` | `postgresql+asyncpg://chat:chat@postgres:5432/chat` | Overwrite only for standalone runs. |
| `GEMINI_MODEL` | `gemini-pro` | Change model version if needed. |

## 3. API reference
Open the interactive docs in browser:
```
http://localhost:8000/docs      # Swagger-UI
http://localhost:8000/redoc     # ReDoc
```

Main endpoints:
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health-check |
| POST | `/chat/ask` | Ask a question (`{"question": "…"}`) |
| GET | `/metrics` | Prometheus metrics |

Rate-limit: **10 requests per minute** per IP.

## 4. Example cURL request
```bash
curl -X POST http://localhost:8000/chat/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Какие ставки по кредиту для малого бизнеса?"}'
```
Response:
```json
{
  "answer": "…текст с условиями…",
  "session_id": "8e3c0fa1-9caf-4c8e-bc9c-2a9b03f3e5bf"
}
```

## 5. Development workflow
```powershell
# setup venv & install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r chat-service/requirements.txt

# run FastAPI locally (expects Postgres running via Docker)
uvicorn chat-service.app.main:app --reload

# run test-suite
pytest -q

# run linters & formatters
pre-commit run --all-files
```

## 6. Running the ETL job manually
Place your CSV (column `text`) in `etl_job/data/source.csv` and run:
```powershell
# build only etl image
docker compose --profile etl build etl_job

# execute one-off ETL
docker compose --profile etl run --rm etl_job /etl/etl_load.py /etl/data/source.csv
```
The script splits documents, embeds them and loads into Postgres (`document` table).

## 7. Testing & QA
* Unit tests – `pytest` (`tests/` folder)
* Static analysis – Black, isort, flake8, Pyright (pre-commit)
* Observability – `/metrics` for Prometheus, structured logs in container output.

---
© 2025 Chatbot-for-Bank-Lending MVP 
