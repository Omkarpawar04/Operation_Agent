# Operation Agent — Local Run and Demo Guide

This guide explains how to start the FINXL Operation Agent app on Windows using PowerShell. It covers the React frontend, Node API, PostgreSQL database, and optional Python services, including the embedded FINXL chatbot.

> Use the same project folder for every command. The examples below use `C:\Users\Aditya\OneDrive\Desktop\Operation_Agent`. Confirm it is on the intended branch with `git branch --show-current`.

## What runs in this project

| Part | Technology | Local address | Required? |
|---|---|---|---|
| Web app | React + Vite | `http://localhost:5173` | Yes |
| Main API and login | Node + Express | `http://localhost:3001` | Yes |
| Database | PostgreSQL | `localhost:5432` | Yes |
| FINXL chatbot API | Python + Flask | `http://127.0.0.1:5001` | For free-form chatbot answers |
| Q&A Generator API | Python + Flask | `http://127.0.0.1:5000` | Only to use Q&A generation |
| Resume Optimizer API | Python + FastAPI | `http://127.0.0.1:8000` | Only to use Resume Optimizer |

The floating assistant button opens the FINXL chatbot in a compact overlay on the current page; it does not navigate away. Its five built-in topic menus and fixed answers work without Gemini. Free-form answers use the Python chatbot API and Gemini. The assistant pauses while a learning quiz or mock interview is active, and resumes after submission or when the interview ends.

## Requirements

- Windows 10/11 and PowerShell
- Git
- Node.js 22.12+ (or 20.19+) and npm
- PostgreSQL 15 or newer, with its Windows service running
- Python 3.11+ for the optional Q&A and Resume services

Check that PostgreSQL is running:

```powershell
Get-Service *postgres* | Select-Object Name, Status
```

If its status is `Stopped`, start the installed PostgreSQL service from Windows Services, then continue.

## 1. Configure local environment files

Open PowerShell in the project root:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent
git branch --show-current
```

The branch should show `Chatbot-AI` if that is the branch you intend to run.

Create local environment files from the examples. These commands do not overwrite existing files:

```powershell
if (-not (Test-Path .\backend\.env)) { Copy-Item .\backend\.env.example .\backend\.env }
if (-not (Test-Path .\frontend\.env)) { Copy-Item .\frontend\.env.example .\frontend\.env }
notepad .\backend\.env
```

In `backend\.env`, set the PostgreSQL connection values to match your local PostgreSQL installation:

```dotenv
PGUSER=postgres
PGHOST=localhost
PGPORT=5432
PGDATABASE=finxl_platform
PGPASSWORD=your_local_postgres_password
API_PORT=3001
AUTH_SECRET=your_generated_secret
FRONTEND_ORIGIN=http://localhost:5173
```

Generate a private `AUTH_SECRET` in PowerShell:

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Copy the generated output into `AUTH_SECRET`. Do not share or commit `.env` files. Keep `AI_API_KEY` in `backend\.env`; never put it in `frontend\.env`.

For Q&A Generator and Resume Optimizer AI responses, set a valid `AI_API_KEY` in `backend\.env`. These services read the shared backend environment file. The main login/API can run without an AI key.

The frontend example already points at the local Node API and optional Python services. Keep its service addresses as:

```dotenv
VITE_API_URL=http://localhost:3001/api
QNA_SERVICE_URL=http://127.0.0.1:5000
RESUME_SERVICE_URL=http://127.0.0.1:8000
CHATBOT_SERVICE_URL=http://127.0.0.1:5001
```

## 2. Install Node dependencies

In a PowerShell terminal:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend
npm ci
```

In a second terminal:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\frontend
npm ci
```

Install dependencies again only if `node_modules` is missing or the lock file has changed.

## 3. Create and seed the local database

Run this once for a new local database, or when you intentionally need to apply the current schema and demo seed data:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend
npm run db:setup
```

The setup script uses `backend\.env`, creates `PGDATABASE` if it does not exist, applies the schema, and inserts demo records. It is designed to be re-runnable. Do not add `--reset` unless you intentionally want to drop the database's public schema and rebuild it; that removes existing tables and data.

If your database is already created and seeded, skip this step. If startup reports that the database does not exist, check `PGDATABASE` in `backend\.env` and run `npm run db:setup` from the backend folder.

## 4. Start the main Node backend

Use a dedicated terminal and leave it running:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend
npm start
```

Successful startup should include:

```text
Backend server running on port 3001
Database test query successful at: ...
```

If you see a database connection error, check that PostgreSQL is running and that `PGUSER`, `PGHOST`, `PGPORT`, `PGDATABASE`, and `PGPASSWORD` in `backend\.env` match your local database.

## 5. Start the frontend

Use another terminal and leave it running:

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\frontend
npm run dev
```

Open the URL printed by Vite, usually `http://localhost:5173`. Sign in with a demo account created by the seed script. For example:

| Role | Email | Local demo password |
|---|---|---|
| Admin | `admin@finxl.com` | `admin123` |
| Operations | `operations@finxl.com` | `operations123` |
| Placement | `placement@finxl.com` | `placement123` |
| Trainer | `trainer@finxl.com` | `trainer123` |
| Student | `student@finxl.com` | `student123` |

These are development-only accounts. Do not use them in a deployed or production environment. If a demo account was created earlier with a different password, rerunning the seed does not overwrite an existing user's password.

## 6. Start the chatbot API

Start a separate PowerShell terminal. The chatbot Python service reads the shared `backend\.env` file, so it uses the same Gemini key without putting the key in the frontend.

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend\chatbot_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python chatbot.py
```

The chatbot API runs on `http://127.0.0.1:5001`. Keep this terminal open for free-form AI answers. The fixed FAQ answers are built into the frontend and can still be selected if this service is stopped.

## 7. Start optional Python services

The main website, login, and database-backed pages need only PostgreSQL, Node, and Vite. Start a Python service in its own terminal only when you want to use that feature.

### Q&A Generator (port 5000)

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend\qna_generator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The Q&A Generator needs `AI_API_KEY` configured in `backend\.env` for Gemini-generated questions. Keep the Q&A terminal open while using that page.

### Resume Optimizer (port 8000)

```powershell
cd C:\Users\Aditya\OneDrive\Desktop\Operation_Agent\backend\resume_optimizer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The Resume Optimizer uses the `AI_API_KEY` in `backend\.env` for AI features. Leave its terminal open while using that page.

## Start-up checklist

For the standard app, keep these three running:

1. PostgreSQL service
2. Node backend (`npm start`, port 3001)
3. Frontend (`npm run dev`, port 5173)
4. Chatbot API (`python chatbot.py`, port 5001) for free-form answers

For Q&A or Resume features, also keep the corresponding Python service running on port 5000 or 8000.

To stop a terminal service, press **Ctrl+C** in that service's terminal. Stop PostgreSQL separately only if you started it just for this local session.

## Troubleshooting

### `client password must be a string`

The backend did not receive `PGPASSWORD`. Confirm the actual file is named `backend\.env` (not `.env.example` or `.env.txt`), enter the local PostgreSQL password there, then restart `npm start`.

### `database "finxl_platform" does not exist`

Confirm `PGDATABASE` in `backend\.env`. If `finxl_platform` is the intended local database, run `npm run db:setup` from `backend`.

### Login shows “Server error”

Read the Node backend terminal for the `Database query error:` line. Fix the database/configuration issue shown there, then restart the backend.

### Login says “Invalid email or password”

Confirm the database setup/seed completed and use a demo account above. The seed script does not replace passwords on existing accounts.

### `express` or another Node package is missing

Run `npm ci` from the folder whose package is missing: `backend` for Express or `frontend` for Vite/React.

### Q&A or Resume feature cannot reach its service

Start the relevant Python service and confirm it is listening on port 5000 (Q&A) or 8000 (Resume). Restart Vite after changing `frontend\.env`.

### Chatbot free-form questions show an unavailable message

Start `backend\chatbot_service\chatbot.py`, confirm it is listening on port 5001, and check that `AI_API_KEY` is set in `backend\.env`. Restart Vite after changing `CHATBOT_SERVICE_URL`.

### Port is already in use

Stop the older process using that port with **Ctrl+C** in its terminal, then restart the service. The Node server checks port 3001 and exits if another server already owns it.

## Security reminders

- Keep `backend\.env` and `frontend\.env` local; never commit them.
- Never put database credentials, `AUTH_SECRET`, or Gemini API keys in frontend code or `frontend\.env`.
- Use fresh secrets and non-demo accounts outside local development.
- Do not expose the Flask development server directly to the internet.

