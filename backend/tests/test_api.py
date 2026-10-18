import io
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app import create_app, db
from app.models import AIUsageDaily, ComplaintHistory, User


def submit(client, headers, **overrides):
    data = {
        "title": overrides.get("title", "Broken classroom projector"),
        "description": overrides.get("description", "The projector in room 204 stopped working yesterday."),
        "location": overrides.get("location", "Building A, room 204"),
        "category": overrides.get("category", "Classroom Equipment"),
    }
    if "ai_consent" in overrides:
        data["ai_consent"] = overrides["ai_consent"]
    return client.post("/api/v1/complaints", data=data, headers=headers)


def test_student_registration_hashes_password_and_rejects_duplicate(client):
    payload = {"name": "Student One", "email": "student@example.edu", "password": "secure-demo-password"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert "token" in response.get_json()["data"]
    with client.application.app_context():
        account = db.session.execute(db.select(User)).scalar_one()
        assert account.password_hash != payload["password"]
        assert account.check_password(payload["password"])
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_app_rejects_missing_signing_secrets(monkeypatch, tmp_path):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(
            {
                "TESTING": True,
                "AI_ENABLED": False,
                "AI_DAILY_LIMIT": 25,
                "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            }
        )


def test_app_rejects_reused_signing_secrets(tmp_path):
    shared_secret = "long-enough-secret-value-for-both"
    with pytest.raises(RuntimeError, match="must be different"):
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": shared_secret,
                "JWT_SECRET_KEY": shared_secret,
                "AI_ENABLED": False,
                "AI_DAILY_LIMIT": 25,
                "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            }
        )


def test_registration_does_not_allow_privilege_escalation(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bad Actor",
            "email": "bad@example.edu",
            "password": "secure-demo-password",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["user"]["role"] == "student"


def test_local_frontend_origins_pass_cors_preflight(client):
    for origin in (
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ):
        response = client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.headers["Access-Control-Allow-Origin"] == origin


def test_student_can_only_access_owned_complaints(client, auth_headers):
    first = auth_headers("first@example.edu")
    second = auth_headers("second@example.edu")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        created = submit(client, first)
    public_id = created.get_json()["data"]["complaint"]["public_id"]
    assert created.status_code == 201
    assert client.get(f"/api/v1/complaints/{public_id}", headers=second).status_code == 404
    mine = client.get("/api/v1/complaints/my", headers=first)
    assert mine.get_json()["data"]["pagination"]["total"] == 1


def test_gemini_failure_keeps_complaint_for_manual_review(client, auth_headers):
    student = auth_headers("fallback@example.edu")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        response = submit(client, student, ai_consent="true")
    complaint = response.get_json()["data"]["complaint"]
    assert response.status_code == 201
    assert complaint["ai_processing_status"] == "Failed"
    assert complaint["status"] == "Submitted"
    with client.application.app_context():
        entry = db.session.execute(
            db.select(ComplaintHistory).where(ComplaintHistory.event_type == "ai_analysis_failed")
        ).scalar_one()
        assert entry.comment == "Manual review required."


def test_daily_ai_limit_caps_paid_analysis(client, auth_headers, app):
    student = auth_headers("daily-limit@example.edu")
    app.config["AI_DAILY_LIMIT"] = 1
    result = {
        "category": "Classroom Equipment",
        "priority": "Medium",
        "summary": "A classroom projector is not working.",
        "department": "Classroom Support",
        "explanation": "The report concerns a classroom projector.",
        "review_flag": False,
    }
    with patch("app.routes.analyze_complaint", return_value=result) as analyze:
        first = submit(client, student, ai_consent="true")
        second = submit(
            client,
            student,
            ai_consent="true",
            title="Broken classroom screen",
        )

    assert first.get_json()["data"]["complaint"]["ai_processing_status"] == "Completed"
    assert second.get_json()["data"]["complaint"]["ai_processing_status"] == "Failed"
    assert "daily AI analysis limit" in second.get_json()["data"]["complaint"]["ai_explanation"]
    analyze.assert_called_once()
    with app.app_context():
        usage = db.session.get(AIUsageDaily, datetime.now(timezone.utc).date())
        assert usage.request_count == 1


def test_ai_disabled_setting_prevents_paid_analysis(client, auth_headers, app):
    student = auth_headers("ai-disabled@example.edu")
    app.config["AI_ENABLED"] = False
    with patch("app.routes.analyze_complaint") as analyze:
        response = submit(client, student, ai_consent="true")
    complaint = response.get_json()["data"]["complaint"]

    assert response.status_code == 201
    assert complaint["ai_processing_status"] == "Failed"
    assert "disabled" in complaint["ai_explanation"]
    analyze.assert_not_called()


def test_ai_analysis_requires_and_records_student_consent(client, auth_headers):
    student = auth_headers("consent@example.edu")
    with patch("app.routes.analyze_complaint") as analyze:
        created = submit(client, student)
        complaint = created.get_json()["data"]["complaint"]
        assert created.status_code == 201
        assert complaint["ai_consent"] is False
        assert complaint["ai_processing_status"] == "Pending"
        analyze.assert_not_called()

        result = {
            "category": "Classroom Equipment",
            "priority": "Medium",
            "summary": "A classroom projector is not working.",
            "department": "Classroom Support",
            "explanation": "The report concerns a classroom projector.",
            "review_flag": False,
        }
        analyze.return_value = result
        response = client.post(
            f"/api/v1/complaints/{complaint['public_id']}/analyze",
            json={"consent": True},
            headers=student,
        )
    assert response.status_code == 200
    assert response.get_json()["data"]["complaint"]["ai_consent"] is True
    assert response.get_json()["data"]["complaint"]["ai_processing_status"] == "Completed"
    analyze.assert_called_once()


def test_status_transition_requires_admin_and_resolution_note(client, auth_headers):
    student = auth_headers("status@example.edu")
    admin = auth_headers("admin@example.edu", role="admin")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        response = submit(client, student)
    public_id = response.get_json()["data"]["complaint"]["public_id"]

    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "In Progress"},
        headers=admin,
    ).status_code == 403
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "Under Review"},
        headers=student,
    ).status_code == 403

    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "Under Review"},
        headers=admin,
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/assign",
        json={"department": "Classroom Support"},
        headers=admin,
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "In Progress"},
        headers=admin,
    ).status_code == 403


def test_staff_work_requires_assignment_and_admin_verification(client, auth_headers):
    student = auth_headers("work@example.edu")
    admin = auth_headers("work-admin@example.edu", role="admin")
    staff = auth_headers("worker@example.edu", role="staff", department="Classroom Support")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        response = submit(client, student)
    public_id = response.get_json()["data"]["complaint"]["public_id"]

    with client.application.app_context():
        staff_user = db.session.execute(db.select(User).where(User.email == "worker@example.edu")).scalar_one()
        staff_id = staff_user.id
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "Under Review"},
        headers=admin,
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/assign",
        json={"department": "Classroom Support", "staff_id": staff_id},
        headers=admin,
    ).status_code == 200
    assert client.post(
        f"/api/v1/staff/complaints/{public_id}/accept",
        headers=staff,
    ).status_code == 200
    update = client.post(
        f"/api/v1/staff/complaints/{public_id}/resolution",
        json={"comment": "Replaced the faulty display cable."},
        headers=staff,
    )
    assert update.status_code == 200
    assert update.get_json()["data"]["complaint"]["status"] == "In Progress"
    assert client.post(
        f"/api/v1/admin/complaints/{public_id}/status",
        json={"status": "Resolved", "comment": "Reviewed and verified the repair."},
        headers=admin,
    ).status_code == 200
    reopened = client.post(
        f"/api/v1/complaints/{public_id}/reopen",
        json={"comment": "The projector stopped working again today."},
        headers=student,
    )
    assert reopened.status_code == 200
    assert reopened.get_json()["data"]["complaint"]["status"] == "Reopened"


def test_upload_rejects_non_image(client, auth_headers):
    student = auth_headers("upload@example.edu")
    response = client.post(
        "/api/v1/complaints",
        data={
            "title": "Water leak",
            "description": "Water is leaking from the sink near the dining hall.",
            "category": "Plumbing",
            "attachment": (io.BytesIO(b"not an image"), "photo.png"),
        },
        headers=student,
    )
    assert response.status_code == 400


def test_admin_analytics_reflect_database(client, auth_headers):
    student = auth_headers("analytics-student@example.edu")
    admin = auth_headers("analytics-admin@example.edu", role="admin")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        submit(client, student)
    response = client.get("/api/v1/admin/analytics", headers=admin)
    assert response.status_code == 200
    assert response.get_json()["data"]["total"] == 1


def test_admin_can_filter_by_date_and_invalid_dates_are_rejected(client, auth_headers):
    student = auth_headers("date-student@example.edu")
    admin = auth_headers("date-admin@example.edu", role="admin")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        submit(client, student)
    today = datetime.now(timezone.utc).date().isoformat()
    response = client.get(
        f"/api/v1/admin/complaints?from_date={today}&to_date={today}",
        headers=admin,
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["pagination"]["total"] == 1
    invalid = client.get("/api/v1/admin/complaints?from_date=not-a-date", headers=admin)
    assert invalid.status_code == 400


def test_admin_csv_escapes_formula_like_titles(client, auth_headers):
    student = auth_headers("csv-student@example.edu")
    admin = auth_headers("csv-admin@example.edu", role="admin")
    with patch("app.routes.analyze_complaint", side_effect=TimeoutError):
        submit(
            client,
            student,
            title="=HYPERLINK(\"https://example.invalid\")",
        )
    report = client.get("/api/v1/admin/reports", headers=admin)
    assert report.status_code == 200
    assert "'=HYPERLINK" in report.get_data(as_text=True)


def test_logout_revokes_token(client, auth_headers):
    headers = auth_headers("logout@example.edu")
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
