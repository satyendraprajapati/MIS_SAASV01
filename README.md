# SaaS Sales BI — AI-Powered Sales Intelligence Platform

## Folder Structure

```
SAAS_SALES_PROJECT/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── core/             # Config, security (JWT, hashing)
│   │   ├── db/               # SQLAlchemy engine & session
│   │   ├── models/           # ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic
│   │   └── main.py           # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client & API functions
│   │   ├── pages/            # Route-level React components
│   │   ├── store/            # Zustand global state
│   │   ├── hooks/            # Custom React hooks
│   │   ├── utils/            # Helper functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

## Setup — Backend

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
copy .env.example .env        # Windows
# cp .env.example .env         # macOS/Linux
# Edit .env — set DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY

# 5. Create the PostgreSQL database
# Open psql or pgAdmin and run:
#   CREATE DATABASE saas_sales_db;

# 6. Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000
API docs (Swagger): http://localhost:8000/docs

## Setup — Frontend

```bash
# 1. Open a new terminal, navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start the dev server
npm run dev
```

Frontend runs at: http://localhost:5173

## API Endpoints

| Method | Endpoint              | Description        |
|--------|-----------------------|--------------------|
| GET    | /health               | Health check       |
| POST   | /api/v1/auth/register | Register user      |
| POST   | /api/v1/auth/login    | Login → JWT tokens |

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python 3.11, FastAPI, Uvicorn     |
| Database  | PostgreSQL 15, SQLAlchemy 2, Alembic |
| Auth      | JWT (python-jose), bcrypt         |
| Frontend  | React 18, Vite, TypeScript        |
| Styling   | Tailwind CSS                      |
| State     | Zustand                           |
| Data Fetch| TanStack Query (React Query v5)   |
| Charts    | Recharts                          |
