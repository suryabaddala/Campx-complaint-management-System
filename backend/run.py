import os
from app import create_app, db

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create local development tables. Use Flask-Migrate for production."""
    db.create_all()
    print("CampusFix tables are ready.")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting CampusFix AI backend on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=True)

