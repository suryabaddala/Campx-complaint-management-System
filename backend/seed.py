import os
import sys

from app import create_app, db
from app.models import User
from app.services.ai_service import DEPARTMENTS


def create_account(email, name, password, role, department=None):
    if not email or not password or password.startswith("change-this"):
        raise ValueError(f"Set a real development password for {email or role} in backend/.env.")
    normalized_email = email.strip().lower()
    user = db.session.execute(db.select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if user:
        return False
    user = User(name=name, email=normalized_email, role=role, department=department)
    user.set_password(password)
    db.session.add(user)
    return True


app = create_app()
with app.app_context():
    db.create_all()
    try:
        create_account(
            os.getenv("ADMIN_EMAIL", ""),
            os.getenv("ADMIN_NAME", "Campus Administrator"),
            os.getenv("ADMIN_PASSWORD", ""),
            "admin",
        )
        if os.getenv("DEMO_STAFF_EMAIL") and os.getenv("DEMO_STAFF_PASSWORD"):
            department = os.getenv("DEMO_STAFF_DEPARTMENT", DEPARTMENTS[0])
            if department not in DEPARTMENTS:
                raise ValueError("DEMO_STAFF_DEPARTMENT must be an approved department.")
            create_account(
                os.getenv("DEMO_STAFF_EMAIL"),
                os.getenv("DEMO_STAFF_NAME", "Maintenance Staff"),
                os.getenv("DEMO_STAFF_PASSWORD"),
                "staff",
                department,
            )
        if os.getenv("DEMO_STUDENT_EMAIL") and os.getenv("DEMO_STUDENT_PASSWORD"):
            create_account(
                os.getenv("DEMO_STUDENT_EMAIL"),
                os.getenv("DEMO_STUDENT_NAME", "Demo Student"),
                os.getenv("DEMO_STUDENT_PASSWORD"),
                "student",
            )
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        print(error, file=sys.stderr)
        raise SystemExit(1)
    print("Development database initialized; configured demo accounts are ready.")
