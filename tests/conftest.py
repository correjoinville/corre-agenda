import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")

import pytest
from app import create_app, get_db
from werkzeug.security import generate_password_hash

@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "DATABASE": str(tmp_path / "test.db"), "IMPORT_FOLDER": str(tmp_path / "imports"), "TODAY_OVERRIDE": "2026-09-20"})
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO admins(username,password_hash,created_at) VALUES(?,?,?)", ("admin", generate_password_hash("secret"), "2026-09-20"))
        db.execute("INSERT INTO events(event_date,name,city,state,registration_url,photos_url,status,slug,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("2026-09-21", "Prova Teste", "Joinville", "SC", "https://example.com", "", "publicado", "prova-teste", "2026", "2026"))
        db.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def logged(client):
    client.post("/login", data={"username": "admin", "password": "secret"})
    return client
