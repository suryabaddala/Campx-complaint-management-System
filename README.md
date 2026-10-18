# CampusFix AI

CampusFix AI is a student-friendly college complaint and resolution portal.
Students can report campus issues, follow their progress, and opt in to
AI-assisted triage. Campus administrators review reports, route work, and
verify resolutions. Maintenance staff see only work assigned to them.

The project uses a React/Vite interface, Flask REST API, SQLAlchemy data models,
SQLite for local development (PostgreSQL-compatible configuration), and the
official Google Gemini SDK for optional server-side analysis.

## What works

- Student account registration, sign-in, sign-out, and hashed passwords.
- Separate student, administrator, and maintenance-staff views.
- Complaint submission, private image attachments, ownership checks, search,
  filtering, pagination, history, comments, and student notifications.
- Optional Gemini classifications, priority, summary, department suggestion,
  explanation, and human-review flag. Students explicitly opt in first.
- Deterministic category-to-department routing. AI never assigns work or
  verifies repairs.
- Staff assignment, progress notes, administrator-verified resolution,
  controlled status transitions, and a 30-day student reopen window.
- Admin analytics, actual average-resolution-time calculations, and CSV export.
- Automated backend and frontend tests. Gemini calls are mocked in the suite.

## Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer with npm
- Optional Google Gemini API key for live AI analysis

## Windows setup (PowerShell)

Run these commands from the project root:

```powershell
py -3 -m venv .\backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
Copy-Item .\backend\.env.example .\backend\.env
```

Edit `backend\.env` and replace both secret values. Set a strong
`ADMIN_PASSWORD` for the local administrator account. You may leave
`GEMINI_API_KEY` blank; reports still save and staff can triage them manually.
Generate separate secrets with this command twice, and paste each generated
value into its corresponding setting:

```powershell
.\backend\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

AI is disabled by default. To opt in, set `GEMINI_API_KEY` and
`AI_ENABLED=true` in this backend-only environment file. `AI_DAILY_LIMIT=25`
caps the entire installation at 25 Gemini requests per UTC day; set it to `0`
to disable paid analysis. Requests are counted before they are sent, including
failed calls. This is a request-count safeguard, not a guaranteed dollar cap:
review the current Gemini pricing and configure a billing budget/alert with
Google. Never put the key in a frontend file or commit `.env`.

Initialize the local database and create the configured administrator:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m flask --app run.py init-db
.\.venv\Scripts\python.exe seed.py
```

Optionally add a development staff account by setting `DEMO_STAFF_EMAIL`,
`DEMO_STAFF_PASSWORD`, and `DEMO_STAFF_DEPARTMENT` in `backend\.env`, then run
`.\.venv\Scripts\python.exe seed.py` again. Departments must match an approved
department name, such as `Electrical Maintenance` or `Classroom Support`.

In a **first PowerShell window**, from `backend`:

```powershell
.\.venv\Scripts\python.exe run.py
```

The backend starts at `http://localhost:5001`. (Port 5001 is used by default to avoid port collisions with other local services on port 5000).

In a **second PowerShell window**, from the project root:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`).

Preconfigured demo accounts for testing:
- **Administrator**: `admin@college.edu` / `AdminCampusFix2026!`
- **Maintenance Staff**: `staff@college.edu` / `StaffCampusFix2026!`
- **Student**: `student@college.edu` / `StudentCampusFix2026!` (or register a new student account)

## Database migrations

Local demos can use `init-db`. For schema changes and deployment, use
Flask-Migrate instead:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m flask --app run.py db init
.\.venv\Scripts\python.exe -m flask --app run.py db migrate -m "Initial schema"
.\.venv\Scripts\python.exe -m flask --app run.py db upgrade
```

Commit the generated migration files with source changes. Apply migrations
before deploying an updated application.

## Tests and production build

From the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests -q
Set-Location .\frontend
npm test
npm run build
```

Test and integration details are in [docs/testing.md](./docs/testing.md).
The API routes are listed in [docs/api.md](./docs/api.md), and the
trust boundaries/data model are described in [docs/architecture.md](./docs/architecture.md).

## Deployment configuration

- Use HTTPS and a persistent PostgreSQL service; set `DATABASE_URL` to its
  SQLAlchemy URL. SQLite is intended for local development and a single
  process, not a multi-worker production deployment.
- Set unique, randomly generated `SECRET_KEY` and `JWT_SECRET_KEY` values,
  store them and `GEMINI_API_KEY` in the hosting provider's secret manager,
  and use a restricted `FRONTEND_ORIGIN`.
- Keep `AI_ENABLED=false` unless the institution has approved AI processing.
  If enabled, the database-backed daily request cap applies across users and
  app workers. Configure provider-side spending alerts as a separate control.
- Set `VITE_API_URL` to the deployed API URL and build the frontend with
  `npm run build`.
- Serve the API with a production WSGI server (for example, Gunicorn behind a
  TLS-terminating reverse proxy); never expose Flask's development server.
- Configure a persistent private upload volume, backups, a distributed rate
  limit store, account recovery, monitoring, retention/deletion, and an
  institution-approved staff onboarding process before real use.
- Add a verified deployment migration step and test restoration from backups.

## Important limitations

This is a teaching/demo MVP, not a ready-to-deploy college system. It has
role-based account creation and server-side permission checks but does not
include institutional identity/SSO, email verification or password recovery,
CSRF-protected cookie sessions, a separate staff work-acceptance state,
configurable campus emergency policy, configurable retention/deletion,
production-grade distributed rate limiting, or malware scanning/image
re-encoding. JWTs are stored in browser local storage, so an XSS flaw could
expose a session. Use only synthetic student information until those
production safeguards and an institutional security review are in place.
Public student accounts can still use up the configured AI request allowance
when AI is enabled; the daily cap bounds spend exposure but does not provide
email verification or protect AI availability for other students.

CampusFix AI is not an emergency response service. For an immediate threat,
injury, or safety emergency, contact campus security or local emergency
services directly.
