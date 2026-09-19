import os
import tempfile
from datetime import date, timedelta

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_PASSWORD", "SenhaTeste123!")
from app import create_app, init_database


@pytest.fixture()
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "DATABASE": path, "TODAY_OVERRIDE": "2026-09-19"})
    with app.app_context():
        init_database(seed=False)
    yield app
    os.close(fd)
    os.unlink(path)


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "admin", "password": "SenhaTeste123!"}, follow_redirects=True)


def add_event(client, **overrides):
    data = {"event_date": "2026-09-20", "name": "Corrida Teste", "city": "Joinville", "state": "SC", "registration_url": "https://example.com/i", "photos_url": "", "status": "publicado"}
    data.update(overrides)
    return client.post("/admin/eventos/novo", data=data, follow_redirects=True)


def test_login_logout_and_protected_route(client):
    assert client.get("/admin").status_code == 302
    assert "Corridas" in login(client).get_data(as_text=True)
    response = client.post("/logout", follow_redirects=True)
    assert "Administração" in response.get_data(as_text=True)


def test_create_edit_delete(client):
    login(client)
    assert "Corrida Teste" in add_event(client).get_data(as_text=True)
    response = client.post("/admin/eventos/1/editar", data={"event_date": "2026-09-21", "name": "Corrida Editada", "city": "Blumenau", "state": "SC", "registration_url": "", "photos_url": "https://example.com/f", "status": "publicado"}, follow_redirects=True)
    assert "Corrida Editada" in response.get_data(as_text=True)
    assert "Nenhuma corrida" in client.post("/admin/eventos/1/excluir", follow_redirects=True).get_data(as_text=True)


def test_public_rules_grouping_and_drafts(client):
    login(client)
    add_event(client, name="Futura Setembro", event_date="2026-09-20")
    add_event(client, name="Futura Outubro", event_date="2026-10-04")
    add_event(client, name="Antiga Visível", event_date="2026-09-04", registration_url="", photos_url="")
    add_event(client, name="Antiga Oculta", event_date="2026-09-03")
    add_event(client, name="Rascunho", status="rascunho")
    html = client.get("/").get_data(as_text=True)
    assert "Setembro 2026" in html and "Outubro 2026" in html
    assert "Futura Setembro" in html and "Futura Outubro" in html and "Antiga Visível" in html
    assert "Fotos em breve" in html
    assert "Antiga Oculta" not in html and "Rascunho" not in html


def test_validation_rejects_bad_url(client):
    login(client)
    response = add_event(client, registration_url="javascript:alert(1)")
    assert "http:// ou https://" in response.get_data(as_text=True)
