# Testing and integration checks

## Automated tests

From the project root in PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests -q
Set-Location .\frontend
npm test
```

Backend tests use a throwaway SQLite database and mock the Gemini call; ordinary
tests do not need network access or an API key. They cover password hashing,
duplicate registration, role escalation, complaint ownership, AI-failure
fallback, staff assignment and verification, attachment validation, analytics,
and token revocation.

## Optional live Gemini smoke check

Set `GEMINI_API_KEY` in `backend\.env`, sign in as a student, create a complaint,
and select the explicit Gemini consent option. The resulting AI analysis state
and recommendations appear on the complaint detail screen. Do not include
secrets or real student complaints in screenshots or public demos.

## Manual demonstration

1. Register a student account and sign in.
2. Submit a facilities complaint without AI consent; confirm it is saved and
   labelled as awaiting human review.
3. Open its detail page and review the timeline. Optionally opt in to Gemini
   for an AI recommendation.
4. Sign in using the seeded administrator, move the report to **Under Review**,
   assign the appropriate department and a matching staff member, then add a
   student-visible progress update.
5. Sign in using the seeded staff account, accept the assignment, and submit
   work notes. Confirm the report is still in progress.
6. As the administrator, add a verification note and mark it **Resolved**.
   Confirm the student gets an in-app notification and sees the history.
7. Reopen the resolved report as the student, if the issue persists.
8. Review analytics and download a CSV as the administrator.

Use demonstration accounts and synthetic reports only.
