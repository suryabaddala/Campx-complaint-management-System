import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    if connection.__class__.__module__ == "sqlite3":
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__)
    ai_enabled = os.getenv("AI_ENABLED", "false").strip().lower()
    if ai_enabled not in {"true", "false"}:
        raise RuntimeError("AI_ENABLED must be set to true or false.")
    try:
        ai_daily_limit = int(os.getenv("AI_DAILY_LIMIT", "25"))
    except ValueError as error:
        raise RuntimeError("AI_DAILY_LIMIT must be a non-negative integer.") from error
    if ai_daily_limit < 0:
        raise RuntimeError("AI_DAILY_LIMIT must be a non-negative integer.")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{Path(__file__).resolve().parents[1] / 'instance' / 'campusfix.db'}",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=str(Path(__file__).resolve().parents[1] / "uploads"),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        AI_ENABLED=ai_enabled == "true",
        AI_DAILY_LIMIT=ai_daily_limit,
        APP_ENV=os.getenv("APP_ENV", "development"),
        JWT_TOKEN_LOCATION=["headers"],
        RATELIMIT_STORAGE_URI="memory://",
    )
    if test_config:
        app.config.update(test_config)
    for setting in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = app.config[setting]
        if not isinstance(value, str) or len(value) < 32:
            raise RuntimeError(f"{setting} must be configured with at least 32 characters.")
    if app.config["SECRET_KEY"] == app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must be different.")
    if app.config["AI_DAILY_LIMIT"] < 0:
        raise RuntimeError("AI_DAILY_LIMIT must be a non-negative integer.")
    if app.config["AI_ENABLED"] and not app.config["GEMINI_API_KEY"]:
        raise RuntimeError("GEMINI_API_KEY is required when AI_ENABLED=true.")

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    allowed_origins = [app.config["FRONTEND_ORIGIN"]]
    if app.config["APP_ENV"] != "production":
        allowed_origins.extend(
            [
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
            ]
        )
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    from app import models
    from app.routes import api

    app.register_blueprint(api, url_prefix="/api/v1")

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_header, payload):
        from app.models import RevokedToken

        return db.session.get(RevokedToken, payload["jti"]) is not None

    @jwt.unauthorized_loader
    def unauthorized(message):
        return jsonify(error={"code": "unauthorized", "message": message}), 401

    @jwt.invalid_token_loader
    def invalid_token(message):
        return jsonify(error={"code": "invalid_token", "message": message}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify(error={"code": "token_expired", "message": "Please sign in again."}), 401

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error={"code": "file_too_large", "message": "The upload must be 5 MB or smaller."}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        app.logger.exception("Unhandled application error")
        return jsonify(error={"code": "internal_error", "message": "An unexpected error occurred."}), 500

    return app
