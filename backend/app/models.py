from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy import CheckConstraint

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __table_args__ = (
        CheckConstraint("role IN ('student', 'admin', 'staff')", name="ck_user_role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="student", index=True)
    department = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    complaints = db.relationship("Complaint", back_populates="student", foreign_keys="Complaint.student_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
        }


class Complaint(db.Model):
    __table_args__ = (
        CheckConstraint(
            "category IN ('Electrical', 'Plumbing', 'Cleaning and Sanitation', "
            "'Internet and Networking', 'Classroom Equipment', 'Laboratory Equipment', "
            "'Hostel Facilities', 'Security', 'Other')",
            name="ck_complaint_category",
        ),
        CheckConstraint("priority IN ('Low', 'Medium', 'High')", name="ck_complaint_priority"),
        CheckConstraint(
            "status IN ('Submitted', 'Under Review', 'Assigned', 'In Progress', "
            "'Resolved', 'Reopened', 'Closed')",
            name="ck_complaint_status",
        ),
        CheckConstraint(
            "ai_processing_status IN ('Pending', 'Processing', 'Completed', 'Failed')",
            name="ck_complaint_ai_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    public_complaint_id = db.Column(db.String(20), nullable=False, unique=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(180), nullable=False, default="")
    category = db.Column(db.String(48), nullable=False, default="Other", index=True)
    priority = db.Column(db.String(16), nullable=False, default="Medium", index=True)
    status = db.Column(db.String(24), nullable=False, default="Submitted", index=True)
    department = db.Column(db.String(64), nullable=False, default="Other", index=True)
    ai_summary = db.Column(db.String(500), nullable=False, default="")
    ai_suggested_category = db.Column(db.String(48))
    ai_suggested_priority = db.Column(db.String(16))
    ai_suggested_department = db.Column(db.String(64))
    ai_explanation = db.Column(db.String(500), nullable=False, default="")
    ai_review_flag = db.Column(db.Boolean, nullable=False, default=False)
    ai_processing_status = db.Column(db.String(16), nullable=False, default="Pending", index=True)
    ai_consent = db.Column(db.Boolean, nullable=False, default=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    resolution_notes = db.Column(db.String(2000), nullable=False, default="")
    resolved_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    student = db.relationship("User", back_populates="complaints", foreign_keys=[student_id])
    assigned_staff = db.relationship("User", foreign_keys=[assigned_staff_id])
    history = db.relationship("ComplaintHistory", back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintHistory.created_at")
    assignments = db.relationship("Assignment", back_populates="complaint", cascade="all, delete-orphan")
    attachments = db.relationship("Attachment", back_populates="complaint", cascade="all, delete-orphan")

    def to_dict(self, include_private=False):
        data = {
            "id": self.id,
            "public_id": self.public_complaint_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "department": self.department,
            "ai_summary": self.ai_summary,
            "ai_suggested_category": self.ai_suggested_category,
            "ai_suggested_priority": self.ai_suggested_priority,
            "ai_suggested_department": self.ai_suggested_department,
            "ai_explanation": self.ai_explanation,
            "ai_review_flag": self.ai_review_flag,
            "ai_processing_status": self.ai_processing_status,
            "ai_consent": self.ai_consent,
            "assigned_staff": self.assigned_staff.name if self.assigned_staff else None,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "history": [
                entry.to_dict(include_private=include_private)
                for entry in self.history
                if include_private or not entry.is_private
            ],
            "attachments": [
                {"id": item.id, "name": item.original_filename}
                for item in self.attachments
            ],
        }
        if include_private:
            data["student"] = self.student.public_dict()
        return data


class ComplaintHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    event_type = db.Column(db.String(48), nullable=False, index=True)
    old_value = db.Column(db.String(500))
    new_value = db.Column(db.String(500))
    comment = db.Column(db.String(2000), nullable=False, default="")
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    complaint = db.relationship("Complaint", back_populates="history")
    actor = db.relationship("User")

    def to_dict(self, include_private=False):
        return {
            "event_type": self.event_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "comment": self.comment,
            "is_private": self.is_private if include_private else False,
            "actor": self.actor.name if self.actor else "System",
            "created_at": self.created_at.isoformat(),
        }


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    assignment_status = db.Column(db.String(24), nullable=False, default="Assigned")
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    complaint = db.relationship("Complaint", back_populates="assignments")
    staff = db.relationship("User", foreign_keys=[staff_id])


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    storage_path = db.Column(db.String(240), nullable=False, unique=True)
    original_filename = db.Column(db.String(180), nullable=False)
    mime_type = db.Column(db.String(64), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    complaint = db.relationship("Complaint", back_populates="attachments")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    complaint = db.relationship("Complaint")

    def to_dict(self):
        return {
            "id": self.id,
            "public_id": self.complaint.public_complaint_id,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    action = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(48), nullable=False)
    resource_id = db.Column(db.String(64), nullable=False, index=True)
    safe_metadata = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class RevokedToken(db.Model):
    jti = db.Column(db.String(36), primary_key=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class AIUsageDaily(db.Model):
    usage_date = db.Column(db.Date, primary_key=True)
    request_count = db.Column(db.Integer, nullable=False, default=0)
