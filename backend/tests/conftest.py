import pytest

from app import create_app, db


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-with-at-least-thirty-two-characters",
            "JWT_SECRET_KEY": "test-jwt-secret-at-least-thirty-two-characters",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "RATELIMIT_ENABLED": False,
            "GEMINI_API_KEY": "test-key",
            "AI_ENABLED": True,
            "AI_DAILY_LIMIT": 25,
            "FRONTEND_ORIGIN": "http://localhost:5173",
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def factory(email, role="student", department=None):
        from app import db
        from app.models import User

        with app.app_context():
            user = User(name=email.split("@")[0], email=email, role=role, department=department)
            user.set_password("secure-demo-password")
            db.session.add(user)
            db.session.commit()
            return user.id

    return factory


@pytest.fixture
def auth_headers(client, make_user):
    def login(email, role="student", department=None):
        make_user(email, role, department)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "secure-demo-password"},
        )
        return {"Authorization": f"Bearer {response.get_json()['data']['token']}"}

    return login
