import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db, limiter
from app.models import (
    AIUsageDaily,
    Assignment,
    Attachment,
    AuditLog,
    Complaint,
    ComplaintHistory,
    Notification,
    RevokedToken,
    User,
    utcnow,
)
from app.services.ai_service import (
    CATEGORIES,
    CATEGORY_DEPARTMENT,
    DEPARTMENTS,
    PRIORITIES,
    analyze_complaint,
)

api = Blueprint("api", __name__)
STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Reopened", "Closed"]
TRANSITIONS = {
    "Submitted": {"Under Review"},
    "Under Review": {"Submitted", "Assigned"},
    "Assigned": {"Under Review", "In Progress"},
    "In Progress": {"Assigned", "Resolved"},
    "Resolved": {"Closed", "Reopened"},
    "Reopened": {"Under Review", "Assigned"},
    "Closed": set(),
}
IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def respond(data=None, status=200):
    return jsonify(data=data), status


def fail(message, status=400, code="invalid_request"):
    return jsonify(error={"code": code, "message": message}), status


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def require_role(*roles):
    user = current_user()
    if user is None or not user.is_active:
        return None, fail("Your account is unavailable.", 401, "account_unavailable")
    if user.role not in roles:
        return None, fail("You do not have permission to perform this action.", 403, "forbidden")
    return user, None


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    return body


def add_history(complaint, actor_id, event_type, old_value=None, new_value=None, comment="", is_private=False):
    db.session.add(
        ComplaintHistory(
            complaint=complaint,
            actor_id=actor_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            comment=comment[:2000],
            is_private=is_private,
        )
    )


def add_notification(user_id, complaint, message):
    db.session.add(Notification(recipient_id=user_id, complaint=complaint, message=message[:500]))


def add_audit(actor_id, action, complaint, safe_metadata=None):
    db.session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type="complaint",
            resource_id=complaint.public_complaint_id,
            safe_metadata=safe_metadata or {},
        )
    )


def get_complaint_or_404(public_id):
    complaint = db.session.execute(
        db.select(Complaint).where(Complaint.public_complaint_id == public_id.upper())
    ).scalar_one_or_none()
    if complaint is None:
        return None, fail("Complaint not found.", 404, "not_found")
    return complaint, None


def apply_transition(complaint, new_status, actor, comment="", allow_assignment=False):
    if new_status == "Assigned" and not allow_assignment:
        return fail("Use the assignment workflow to route this complaint.", 409, "assignment_required")
    if new_status == "In Progress" and (
        actor.role != "staff" or complaint.assigned_staff_id != actor.id
    ):
        return fail("Only the assigned maintenance staff can accept this work.", 403, "forbidden")
    if new_status in {"Resolved", "Closed"} and actor.role != "admin":
        return fail("Only an administrator can verify or close completed work.", 403, "forbidden")
    if new_status not in STATUSES or new_status not in TRANSITIONS.get(complaint.status, set()):
        return fail(f"Status cannot change from {complaint.status} to {new_status}.", 409, "invalid_transition")
    if new_status == "Resolved" and len(comment.strip()) < 8:
        return fail("Add a resolution note of at least 8 characters before resolving.", 400, "resolution_note_required")
    old_status = complaint.status
    complaint.status = new_status
    if new_status == "Resolved":
        complaint.resolution_notes = comment.strip()
        complaint.resolved_at = utcnow()
    elif old_status == "Resolved" and new_status == "Reopened":
        complaint.resolved_at = None
    complaint.updated_at = utcnow()
    add_history(complaint, actor.id, "status_changed", old_status, new_status, comment)
    add_audit(actor.id, "status_changed", complaint, {"from": old_status, "to": new_status})
    add_notification(complaint.student_id, complaint, f"Your complaint status changed to {new_status}.")
    return None


def paginate(statement, max_per_page=100):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)
    total = db.session.scalar(db.select(func.count()).select_from(statement.subquery()))
    items = db.session.execute(statement.limit(per_page).offset((page - 1) * per_page)).scalars().all()
    return items, {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}


def analyze_saved_complaint(complaint):
    api_key = current_app.config["GEMINI_API_KEY"]
    if not current_app.config["AI_ENABLED"] or not api_key:
        complaint.ai_processing_status = "Failed"
        complaint.ai_explanation = "AI analysis is disabled or not configured. A staff member must review this report."
        add_history(complaint, None, "ai_analysis_failed", comment="AI analysis is disabled or not configured; manual review required.")
        db.session.commit()
        return
    daily_limit = current_app.config["AI_DAILY_LIMIT"]
    if daily_limit == 0 or not reserve_daily_ai_usage(daily_limit):
        complaint.ai_processing_status = "Failed"
        complaint.ai_explanation = "The daily AI analysis limit has been reached. A staff member must review this report."
        add_history(complaint, None, "ai_analysis_failed", comment="Daily AI analysis limit reached; manual review required.")
        db.session.commit()
        return
    complaint.ai_processing_status = "Processing"
    db.session.commit()
    try:
        result = analyze_complaint(
            complaint.title,
            complaint.description,
            complaint.location,
            api_key,
        )
        complaint.ai_suggested_category = result["category"]
        complaint.ai_suggested_priority = result["priority"]
        complaint.ai_suggested_department = result["department"]
        complaint.ai_summary = result["summary"]
        complaint.ai_explanation = result["explanation"]
        complaint.ai_review_flag = result["review_flag"]
        complaint.ai_processing_status = "Completed"
        add_history(complaint, None, "ai_analysis", new_value=result["category"], comment="AI suggestions are unverified and require human review.")
    except Exception as error:
        current_app.logger.warning("Complaint AI analysis failed (%s): %s", complaint.public_complaint_id, type(error).__name__)
        db.session.rollback()
        complaint = db.session.get(Complaint, complaint.id)
        complaint.ai_processing_status = "Failed"
        complaint.ai_explanation = "AI analysis is unavailable. A staff member must review this report."
        add_history(complaint, None, "ai_analysis_failed", comment="Manual review required.")
    db.session.commit()


def reserve_daily_ai_usage(daily_limit):
    usage_date = datetime.now(timezone.utc).date()
    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        insert = sqlite_insert
    elif dialect == "postgresql":
        insert = postgresql_insert
    else:
        raise RuntimeError(f"AI usage quotas do not support database dialect {dialect!r}.")
    usage_table = AIUsageDaily.__table__
    statement = (
        insert(usage_table)
        .values(usage_date=usage_date, request_count=1)
        .on_conflict_do_update(
            index_elements=[usage_table.c.usage_date],
            set_={"request_count": usage_table.c.request_count + 1},
            where=usage_table.c.request_count < daily_limit,
        )
        .returning(usage_table.c.usage_date)
    )
    reserved = db.session.execute(statement).scalar_one_or_none() is not None
    db.session.commit()
    return reserved


@api.get("/health")
def health():
    return respond({"status": "ok"})


@api.post("/auth/register")
@limiter.limit("5 per minute")
def register():
    body = json_body()
    if body is None:
        return fail("Send a JSON request body.")
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip()
    password = body.get("password")
    if not name or len(name) > 100:
        return fail("Name is required and must be 100 characters or fewer.")
    if not isinstance(password, str) or len(password) < 10 or len(password) > 128:
        return fail("Password must be between 10 and 128 characters.")
    try:
        normalized_email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as error:
        return fail(str(error))
    if db.session.execute(db.select(User.id).where(User.email == normalized_email)).first():
        return fail("An account with this email already exists.", 409, "email_exists")
    user = User(name=name, email=normalized_email, role="student")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return respond({"token": token, "user": user.public_dict()}, 201)


@api.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    body = json_body()
    if body is None:
        return fail("Send a JSON request body.")
    email = str(body.get("email", "")).strip().lower()
    password = body.get("password")
    user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not user.is_active or not isinstance(password, str) or not user.check_password(password):
        return fail("Email or password is incorrect.", 401, "invalid_credentials")
    token = create_access_token(identity=str(user.id))
    return respond({"token": token, "user": user.public_dict()})


@api.post("/auth/logout")
@jwt_required()
def logout():
    db.session.add(RevokedToken(jti=get_jwt()["jti"]))
    db.session.commit()
    return respond({"message": "You are signed out."})


@api.get("/auth/me")
@jwt_required()
def me():
    user = current_user()
    if user is None or not user.is_active:
        return fail("Your account is unavailable.", 401, "account_unavailable")
    return respond({"user": user.public_dict()})


@api.post("/complaints")
@jwt_required()
@limiter.limit("10 per hour")
def create_complaint():
    user, error = require_role("student")
    if error:
        return error
    title = str(request.form.get("title", "")).strip()
    description = str(request.form.get("description", "")).strip()
    location = str(request.form.get("location", "")).strip()
    category = str(request.form.get("category", "Other")).strip() or "Other"
    if not title or len(title) > 140:
        return fail("Title is required and must be 140 characters or fewer.")
    if len(description) < 15 or len(description) > 5000:
        return fail("Description must be between 15 and 5,000 characters.")
    if len(location) > 180:
        return fail("Location must be 180 characters or fewer.")
    if category not in CATEGORIES:
        return fail("Choose a category from the approved list.")

    complaint = Complaint(
        public_complaint_id=f"CF-{uuid.uuid4().hex[:8].upper()}",
        student_id=user.id,
        title=title,
        description=description,
        location=location,
        category=category,
        department=CATEGORY_DEPARTMENT[category],
        status="Submitted",
        ai_consent=request.form.get("ai_consent", "").lower() == "true",
    )
    db.session.add(complaint)
    db.session.flush()
    add_history(complaint, user.id, "submitted", new_value="Submitted", comment="Complaint submitted.")
    add_notification(user.id, complaint, f"Your complaint {complaint.public_complaint_id} was received.")

    uploaded = request.files.get("attachment")
    if uploaded and uploaded.filename:
        if len(uploaded.filename) > 180:
            db.session.rollback()
            return fail("File name must be 180 characters or fewer.")
        original_name = secure_filename(uploaded.filename)
        data = uploaded.read(5 * 1024 * 1024 + 1)
        mime_type = next(
            (mime for mime, signature in IMAGE_SIGNATURES.items() if signature(data)),
            None,
        )
        if not mime_type or len(data) > 5 * 1024 * 1024:
            db.session.rollback()
            return fail("Upload a PNG, JPEG, or WebP image up to 5 MB.")
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime_type]
        storage_name = f"{uuid.uuid4().hex}{suffix}"
        target = Path(current_app.config["UPLOAD_FOLDER"]) / storage_name
        target.write_bytes(data)
        db.session.add(
            Attachment(
                complaint=complaint,
                uploaded_by=user.id,
                storage_path=storage_name,
                original_filename=original_name or "campus-photo",
                mime_type=mime_type,
                size_bytes=len(data),
            )
        )
    db.session.commit()
    if complaint.ai_consent:
        analyze_saved_complaint(complaint)
    else:
        complaint.ai_explanation = "AI analysis was not requested. Staff will review the original report."
        db.session.commit()
    return respond({"complaint": complaint.to_dict()}, 201)


@api.get("/complaints/my")
@jwt_required()
def my_complaints():
    user, error = require_role("student")
    if error:
        return error
    statement = db.select(Complaint).where(Complaint.student_id == user.id).order_by(Complaint.created_at.desc())
    status = request.args.get("status")
    if status:
        if status not in STATUSES:
            return fail("Unknown complaint status.")
        statement = statement.where(Complaint.status == status)
    items, pagination = paginate(statement)
    return respond({"items": [item.to_dict() for item in items], "pagination": pagination})


@api.get("/complaints/<public_id>")
@jwt_required()
def complaint_detail(public_id):
    user = current_user()
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if user.role == "student" and complaint.student_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    if user.role == "staff" and complaint.assigned_staff_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    return respond({"complaint": complaint.to_dict(include_private=user.role == "admin")})


@api.post("/complaints/<public_id>/comments")
@jwt_required()
def add_comment(public_id):
    user = current_user()
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if user.role == "student" and complaint.student_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    if user.role == "staff" and complaint.assigned_staff_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    body = json_body() or {}
    comment = str(body.get("comment", "")).strip()
    if not comment or len(comment) > 2000:
        return fail("Comment is required and must be 2,000 characters or fewer.")
    add_history(complaint, user.id, "comment", comment=comment, is_private=bool(body.get("internal")) and user.role == "admin")
    add_notification(complaint.student_id, complaint, "A new update was added to your complaint.")
    db.session.commit()
    return respond({"complaint": complaint.to_dict(include_private=user.role == "admin")}, 201)


@api.post("/complaints/<public_id>/reopen")
@jwt_required()
def reopen_complaint(public_id):
    user, error = require_role("student")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if complaint.student_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    if complaint.status != "Resolved":
        return fail("Only resolved complaints can be reopened.", 409, "invalid_transition")
    if complaint.resolved_at:
        resolved_at = complaint.resolved_at
        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)
        if utcnow() - resolved_at > timedelta(days=30):
            return fail("The 30-day reopening window has passed. Contact campus administration.", 409, "reopen_window_expired")
    body = json_body() or {}
    comment = str(body.get("comment", "")).strip()
    if len(comment) < 8:
        return fail("Explain why the issue persists (at least 8 characters).")
    error = apply_transition(complaint, "Reopened", user, comment)
    if error:
        return error
    db.session.commit()
    return respond({"complaint": complaint.to_dict()})


@api.post("/complaints/<public_id>/analyze")
@jwt_required()
@limiter.limit("5 per hour")
def opt_in_ai_analysis(public_id):
    user, error = require_role("student")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if complaint.student_id != user.id:
        return fail("Complaint not found.", 404, "not_found")
    body = json_body() or {}
    if body.get("consent") is not True:
        return fail("Explicit consent is required before sending report text to Gemini.")
    if complaint.ai_processing_status == "Completed":
        return fail("This complaint has already been analyzed.", 409, "already_analyzed")
    complaint.ai_consent = True
    complaint.ai_processing_status = "Pending"
    db.session.commit()
    analyze_saved_complaint(complaint)
    return respond({"complaint": complaint.to_dict()})


@api.get("/notifications")
@jwt_required()
def notifications():
    user = current_user()
    statement = db.select(Notification).where(Notification.recipient_id == user.id).order_by(Notification.created_at.desc())
    items, pagination = paginate(statement, max_per_page=50)
    return respond({"items": [item.to_dict() for item in items], "pagination": pagination})


@api.patch("/notifications/<int:notification_id>/read")
@jwt_required()
def mark_notification_read(notification_id):
    user = current_user()
    item = db.session.execute(
        db.select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user.id,
        )
    ).scalar_one_or_none()
    if item is None:
        return fail("Notification not found.", 404, "not_found")
    item.is_read = True
    db.session.commit()
    return respond({"notification": item.to_dict()})


@api.get("/admin/complaints")
@jwt_required()
def admin_complaints():
    admin, error = require_role("admin")
    if error:
        return error
    statement = db.select(Complaint).order_by(Complaint.created_at.desc())
    filters = {
        "status": (Complaint.status, STATUSES),
        "category": (Complaint.category, CATEGORIES),
        "priority": (Complaint.priority, PRIORITIES),
        "department": (Complaint.department, DEPARTMENTS),
    }
    for name, (column, allowed) in filters.items():
        value = request.args.get(name)
        if value:
            if value not in allowed:
                return fail(f"Invalid {name} filter.")
            statement = statement.where(column == value)
    for parameter, comparison in (("from_date", "from"), ("to_date", "to")):
        date_value = request.args.get(parameter)
        if not date_value:
            continue
        try:
            parsed_date = date.fromisoformat(date_value)
        except ValueError:
            return fail(f"{parameter} must use YYYY-MM-DD format.")
        boundary = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        if comparison == "from":
            statement = statement.where(Complaint.created_at >= boundary)
        else:
            statement = statement.where(
                Complaint.created_at < boundary + timedelta(days=1)
            )
    query = request.args.get("q", "").strip()
    if len(query) > 100:
        return fail("Search text must be 100 characters or fewer.")
    if query:
        pattern = f"%{query}%"
        statement = statement.join(User, Complaint.student_id == User.id).where(
            db.or_(
                Complaint.public_complaint_id.ilike(pattern),
                Complaint.title.ilike(pattern),
                User.name.ilike(pattern),
            )
        )
    items, pagination = paginate(statement)
    return respond({"items": [item.to_dict(include_private=True) for item in items], "pagination": pagination})


@api.patch("/admin/complaints/<public_id>")
@jwt_required()
def update_admin_complaint(public_id):
    admin, error = require_role("admin")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    body = json_body()
    if body is None:
        return fail("Send a JSON request body.")
    for field, allowed in (("category", CATEGORIES), ("priority", PRIORITIES)):
        if field in body:
            value = str(body[field])
            if value not in allowed:
                return fail(f"Invalid {field}.")
            old = getattr(complaint, field)
            if old != value:
                setattr(complaint, field, value)
                add_history(complaint, admin.id, f"{field}_corrected", old, value)
                add_audit(admin.id, f"{field}_corrected", complaint, {"from": old, "to": value})
    if "department" in body:
        value = str(body["department"])
        if value not in DEPARTMENTS:
            return fail("Invalid department.")
        old = complaint.department
        complaint.department = value
        add_history(complaint, admin.id, "department_changed", old, value)
        add_audit(admin.id, "department_changed", complaint, {"from": old, "to": value})
    if "comment" in body and str(body["comment"]).strip():
        comment = str(body["comment"]).strip()
        if len(comment) > 2000:
            return fail("Comment must be 2,000 characters or fewer.")
        add_history(complaint, admin.id, "comment", comment=comment, is_private=bool(body.get("internal")))
        if not body.get("internal"):
            add_notification(complaint.student_id, complaint, "Campus staff shared an update on your complaint.")
    db.session.commit()
    return respond({"complaint": complaint.to_dict(include_private=True)})


@api.post("/admin/complaints/<public_id>/analyze")
@jwt_required()
def admin_retry_analysis(public_id):
    _, error = require_role("admin")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if not complaint.ai_consent:
        return fail("The student has not consented to AI analysis.", 403, "consent_required")
    complaint.ai_processing_status = "Pending"
    db.session.commit()
    analyze_saved_complaint(complaint)
    return respond({"complaint": complaint.to_dict(include_private=True)})


@api.post("/admin/complaints/<public_id>/assign")
@jwt_required()
def assign_complaint(public_id):
    admin, error = require_role("admin")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    body = json_body() or {}
    department = str(body.get("department", complaint.department))
    staff_id = body.get("staff_id")
    if department not in DEPARTMENTS:
        return fail("Choose an approved department.")
    staff = None
    if staff_id is not None:
        if not isinstance(staff_id, int):
            return fail("staff_id must identify an active staff member.")
        staff = db.session.get(User, staff_id)
        if not staff or staff.role != "staff" or not staff.is_active:
            return fail("Choose an active maintenance staff account.")
        if staff.department and staff.department != department:
            return fail("Staff department must match the complaint department.")
    if complaint.status not in {"Under Review", "Reopened", "Assigned"}:
        return fail("This complaint cannot be assigned in its current status.", 409, "invalid_transition")
    old_department = complaint.department
    old_staff = complaint.assigned_staff_id
    complaint.department = department
    complaint.assigned_staff_id = staff.id if staff else None
    if complaint.status != "Assigned":
        error = apply_transition(complaint, "Assigned", admin, f"Assigned to {department}.", allow_assignment=True)
        if error:
            return error
    add_history(complaint, admin.id, "assignment_changed", str(old_staff) if old_staff else None, str(staff.id) if staff else department)
    add_audit(admin.id, "complaint_assigned", complaint, {"department": department, "staff_id": staff.id if staff else None})
    if staff:
        db.session.add(Assignment(complaint=complaint, staff_id=staff.id, assigned_by=admin.id))
        add_notification(staff.id, complaint, f"Complaint {complaint.public_complaint_id} was assigned to you.")
    add_notification(complaint.student_id, complaint, f"Your complaint was assigned to {department}.")
    if old_department != department:
        add_history(complaint, admin.id, "department_changed", old_department, department)
    db.session.commit()
    return respond({"complaint": complaint.to_dict(include_private=True)})


@api.post("/admin/complaints/<public_id>/status")
@jwt_required()
def admin_status(public_id):
    admin, error = require_role("admin")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    body = json_body() or {}
    status = str(body.get("status", ""))
    comment = str(body.get("comment", "")).strip()
    error = apply_transition(complaint, status, admin, comment)
    if error:
        return error
    db.session.commit()
    return respond({"complaint": complaint.to_dict(include_private=True)})


@api.get("/admin/staff")
@jwt_required()
def list_staff():
    _, error = require_role("admin")
    if error:
        return error
    staff = db.session.execute(
        db.select(User).where(User.role == "staff", User.is_active.is_(True)).order_by(User.name)
    ).scalars().all()
    return respond({"items": [user.public_dict() for user in staff]})


@api.post("/admin/staff")
@jwt_required()
def create_staff():
    admin, error = require_role("admin")
    if error:
        return error
    body = json_body() or {}
    name = str(body.get("name", "")).strip()
    department = str(body.get("department", "")).strip()
    email = str(body.get("email", "")).strip()
    password = body.get("password")
    if not name or len(name) > 100 or department not in DEPARTMENTS:
        return fail("Provide a staff name and an approved department.")
    if not isinstance(password, str) or len(password) < 10 or len(password) > 128:
        return fail("Password must be between 10 and 128 characters.")
    try:
        normalized_email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as error:
        return fail(str(error))
    if db.session.execute(db.select(User.id).where(User.email == normalized_email)).first():
        return fail("An account with this email already exists.", 409, "email_exists")
    staff = User(name=name, email=normalized_email, role="staff", department=department)
    staff.set_password(password)
    db.session.add(staff)
    db.session.flush()
    db.session.add(
        AuditLog(
            actor_id=admin.id,
            action="staff_created",
            resource_type="user",
            resource_id=str(staff.id),
            safe_metadata={"department": department},
        )
    )
    db.session.commit()
    return respond({"user": staff.public_dict()}, 201)


@api.get("/staff/complaints")
@jwt_required()
def staff_complaints():
    staff, error = require_role("staff")
    if error:
        return error
    statement = db.select(Complaint).where(Complaint.assigned_staff_id == staff.id).order_by(Complaint.created_at.desc())
    items, pagination = paginate(statement)
    return respond({"items": [item.to_dict() for item in items], "pagination": pagination})


@api.post("/staff/complaints/<public_id>/accept")
@jwt_required()
def accept_work(public_id):
    staff, error = require_role("staff")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if complaint.assigned_staff_id != staff.id:
        return fail("Complaint not found.", 404, "not_found")
    error = apply_transition(complaint, "In Progress", staff, "Assigned staff accepted the work.")
    if error:
        return error
    db.session.commit()
    return respond({"complaint": complaint.to_dict()})


@api.post("/staff/complaints/<public_id>/resolution")
@jwt_required()
def submit_work_notes(public_id):
    staff, error = require_role("staff")
    if error:
        return error
    complaint, error = get_complaint_or_404(public_id)
    if error:
        return error
    if complaint.assigned_staff_id != staff.id:
        return fail("Complaint not found.", 404, "not_found")
    if complaint.status != "In Progress":
        return fail("Accept this work before submitting progress notes.", 409, "invalid_transition")
    body = json_body() or {}
    comment = str(body.get("comment", "")).strip()
    if len(comment) < 8 or len(comment) > 2000:
        return fail("Work update must be between 8 and 2,000 characters.")
    add_history(complaint, staff.id, "work_completed", new_value="Awaiting administrative verification", comment=comment)
    add_notification(complaint.student_id, complaint, "Maintenance staff added a progress update. Resolution awaits administrative verification.")
    add_audit(staff.id, "work_update_submitted", complaint)
    db.session.commit()
    return respond({"complaint": complaint.to_dict()})


@api.get("/attachments/<int:attachment_id>")
@jwt_required()
def get_attachment(attachment_id):
    user = current_user()
    attachment = db.session.get(Attachment, attachment_id)
    if not attachment:
        return fail("Attachment not found.", 404, "not_found")
    complaint = attachment.complaint
    allowed = (
        user.role == "admin"
        or (user.role == "student" and complaint.student_id == user.id)
        or (user.role == "staff" and complaint.assigned_staff_id == user.id)
    )
    if not allowed:
        return fail("Attachment not found.", 404, "not_found")
    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        attachment.storage_path,
        mimetype=attachment.mime_type,
        as_attachment=False,
        download_name=attachment.original_filename,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@api.get("/admin/analytics")
@jwt_required()
def admin_analytics():
    _, error = require_role("admin")
    if error:
        return error
    total = db.session.scalar(db.select(func.count(Complaint.id)))
    status_rows = db.session.execute(
        db.select(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status)
    ).all()
    category_rows = db.session.execute(
        db.select(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category)
    ).all()
    department_rows = db.session.execute(
        db.select(Complaint.department, func.count(Complaint.id)).group_by(Complaint.department)
    ).all()
    priority_rows = db.session.execute(
        db.select(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority)
    ).all()
    resolved = db.session.execute(
        db.select(Complaint.created_at, Complaint.resolved_at).where(Complaint.resolved_at.is_not(None))
    ).all()
    average_hours = (
        round(sum((end - start).total_seconds() / 3600 for start, end in resolved) / len(resolved), 1)
        if resolved
        else None
    )
    recent = db.session.execute(
        db.select(func.date(Complaint.created_at), func.count(Complaint.id))
        .group_by(func.date(Complaint.created_at))
        .order_by(func.date(Complaint.created_at).desc())
        .limit(14)
    ).all()
    return respond(
        {
            "total": total or 0,
            "active": sum(count for status, count in status_rows if status not in {"Resolved", "Closed"}),
            "high_priority": db.session.scalar(
                db.select(func.count(Complaint.id)).where(Complaint.priority == "High")
            )
            or 0,
            "resolved": sum(count for status, count in status_rows if status in {"Resolved", "Closed"}),
            "average_resolution_hours": average_hours,
            "by_status": [{"name": name, "value": count} for name, count in status_rows],
            "by_category": [{"name": name, "value": count} for name, count in category_rows],
            "by_department": [{"name": name, "value": count} for name, count in department_rows],
            "by_priority": [{"name": name, "value": count} for name, count in priority_rows],
            "trend": [{"date": str(day), "count": count} for day, count in reversed(recent)],
        }
    )


@api.get("/admin/reports")
@jwt_required()
def admin_report():
    _, error = require_role("admin")
    if error:
        return error
    from flask import Response

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Complaint ID", "Title", "Category", "Priority", "Status", "Department", "Created", "Resolved"])

    def csv_safe(value):
        text = str(value or "")
        if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{text}"
        return text

    complaints = db.session.execute(db.select(Complaint).order_by(Complaint.created_at.desc())).scalars()
    for item in complaints:
        writer.writerow(
            [
                csv_safe(item.public_complaint_id),
                csv_safe(item.title),
                csv_safe(item.category),
                csv_safe(item.priority),
                csv_safe(item.status),
                csv_safe(item.department),
                csv_safe(item.created_at.isoformat()),
                csv_safe(item.resolved_at.isoformat() if item.resolved_at else ""),
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=campusfix-report.csv"},
    )
