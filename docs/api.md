# CampusFix AI API

Base URL: `http://localhost:5001/api/v1` (or configured `PORT`). Protected routes require
`Authorization: Bearer <access-token>`. JSON responses use `{ "data": ... }`;
errors use `{ "error": { "code": "...", "message": "..." } }`.

## Authentication

| Method | Route | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a student; client roles are ignored |
| POST | `/auth/login` | Public | Obtain a one-hour JWT |
| POST | `/auth/logout` | Signed in | Revoke the current JWT |
| GET | `/auth/me` | Signed in | Return the current account |

Registration and login are rate-limited. Admin and staff accounts are created
through the administrator workflow or the local seed script; public
registration always creates a student.

## Complaints

| Method | Route | Access | Purpose |
|---|---|---|---|
| POST | `/complaints` | Student | Create a complaint; optional multipart image and AI consent |
| GET | `/complaints/my` | Student | Paginated owned complaints; optional `status` |
| GET | `/complaints/{public_id}` | Owner, assigned staff, admin | View complaint and allowed history |
| POST | `/complaints/{public_id}/comments` | Owner, assigned staff, admin | Add a complaint update |
| POST | `/complaints/{public_id}/reopen` | Owner | Reopen within 30 days of resolution |
| POST | `/complaints/{public_id}/analyze` | Owner | Give explicit consent and request AI analysis |
| GET | `/attachments/{id}` | Owner, assigned staff, admin | View a private uploaded image |

Complaint creation requires a title (up to 140 characters), description
(15–5,000 characters), approved category, and location (up to 180 characters).
Images are optional, limited to 5 MB, and accepted only when their contents
identify them as PNG, JPEG, or WebP.

AI consent is optional and is also checked by the backend. Only the report
title, description, and location are sent to Gemini. Failed or unconfigured AI
analysis does not remove the complaint.

## Administration

| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/admin/complaints` | Admin | Filter/search with `status`, `category`, `priority`, `department`, `from_date`, `to_date`, `q`, `page`, `per_page` |
| PATCH | `/admin/complaints/{public_id}` | Admin | Correct classification / department or add a student-visible/internal note |
| POST | `/admin/complaints/{public_id}/assign` | Admin | Assign a department and optional staff member |
| POST | `/admin/complaints/{public_id}/status` | Admin | Apply a permitted workflow transition |
| POST | `/admin/complaints/{public_id}/analyze` | Admin | Retry AI analysis when the student has consented |
| GET | `/admin/staff` | Admin | List active staff |
| POST | `/admin/staff` | Admin | Create a staff account |
| GET | `/admin/analytics` | Admin | Database-backed totals and breakdowns |
| GET | `/admin/reports` | Admin | Download a CSV summary |

## Maintenance staff

| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/staff/complaints` | Staff | List only work assigned to the current staff account |
| POST | `/staff/complaints/{public_id}/accept` | Assigned staff | Move assigned work into progress |
| POST | `/staff/complaints/{public_id}/resolution` | Assigned staff | Submit work notes for administrator verification |

## Notifications

| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/notifications` | Signed in | List only the current user's notifications |
| PATCH | `/notifications/{id}/read` | Recipient | Mark a notification read |

## Status workflow

`Submitted → Under Review → Assigned → In Progress → Resolved → Closed`.
Resolved complaints may be reopened by the owner within 30 days or by an
administrator. Reopened reports return to review/assignment. Assignments use
the assignment endpoint; status changes use a validated transition table.
Resolution requires an explanatory note. Maintenance staff submit completion
notes but cannot mark a repair verified/resolved.
