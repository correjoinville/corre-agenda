import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

import click
from flask import (Flask, current_app, flash, g, redirect, render_template, request,
                   session, url_for)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash


MONTHS_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.root_path, "database.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Defina a variável de ambiente SECRET_KEY antes de iniciar o site.")

    CSRFProtect(app)
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    @app.template_filter("date_br")
    def date_br(value):
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")

    @app.get("/")
    def index():
        today = get_today(app)
        cutoff = (today - timedelta(days=15)).isoformat()
        events = get_db().execute(
            """SELECT * FROM events
               WHERE status = 'publicado' AND event_date >= ?
               ORDER BY event_date ASC, name COLLATE NOCASE ASC""",
            (cutoff,),
        ).fetchall()
        groups = []
        for event in events:
            event_day = datetime.strptime(event["event_date"], "%Y-%m-%d").date()
            key = (event_day.year, event_day.month)
            if not groups or groups[-1]["key"] != key:
                groups.append({"key": key, "title": f"{MONTHS_PT[event_day.month]} {event_day.year}", "events": []})
            groups[-1]["events"].append(event)
        return render_template("index.html", groups=groups, today=today, months=MONTHS_PT)

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if session.get("admin_id"):
            return redirect(url_for("admin"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            admin = get_db().execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if admin and check_password_hash(admin["password_hash"], password):
                session.clear()
                session["admin_id"] = admin["id"]
                session.permanent = True
                return redirect(url_for("admin"))
            flash("Usuário ou senha inválidos.", "error")
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("Você saiu da área administrativa.", "success")
        return redirect(url_for("login"))

    @app.get("/admin")
    @login_required
    def admin():
        events = get_db().execute(
            "SELECT * FROM events ORDER BY event_date DESC, name COLLATE NOCASE"
        ).fetchall()
        return render_template("admin.html", events=events)

    @app.route("/admin/eventos/novo", methods=("GET", "POST"))
    @login_required
    def event_create():
        if request.method == "POST":
            data, errors = validate_event_form(request.form)
            if not errors:
                now = datetime.now().isoformat(timespec="seconds")
                db = get_db()
                db.execute(
                    """INSERT INTO events
                       (event_date, name, city, state, registration_url, photos_url, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*data, now, now),
                )
                db.commit()
                flash("Corrida adicionada com sucesso.", "success")
                return redirect(url_for("admin"))
            for error in errors:
                flash(error, "error")
        return render_template("event_form.html", event=None, form=request.form)

    @app.route("/admin/eventos/<int:event_id>/editar", methods=("GET", "POST"))
    @login_required
    def event_edit(event_id):
        event = get_event_or_404(event_id)
        if request.method == "POST":
            data, errors = validate_event_form(request.form)
            if not errors:
                db = get_db()
                db.execute(
                    """UPDATE events SET event_date=?, name=?, city=?, state=?, registration_url=?,
                       photos_url=?, status=?, updated_at=? WHERE id=?""",
                    (*data, datetime.now().isoformat(timespec="seconds"), event_id),
                )
                db.commit()
                flash("Corrida atualizada com sucesso.", "success")
                return redirect(url_for("admin"))
            for error in errors:
                flash(error, "error")
        return render_template("event_form.html", event=event, form=request.form)

    @app.post("/admin/eventos/<int:event_id>/excluir")
    @login_required
    def event_delete(event_id):
        event = get_event_or_404(event_id)
        db = get_db()
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        db.commit()
        flash(f'“{event["name"]}” foi excluída.', "success")
        return redirect(url_for("admin"))

    return app


def get_today(app):
    override = app.config.get("TODAY_OVERRIDE")
    return date.fromisoformat(override) if override else date.today()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped


def safe_url(value):
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        return value if parsed.scheme in ("http", "https") and parsed.netloc else None
    except ValueError:
        return None


def validate_event_form(form):
    event_date = form.get("event_date", "").strip()
    name = form.get("name", "").strip()
    city = form.get("city", "").strip()
    state = form.get("state", "").strip().upper()
    registration_url = form.get("registration_url", "").strip()
    photos_url = form.get("photos_url", "").strip()
    status = form.get("status", "").strip()
    errors = []
    try:
        date.fromisoformat(event_date)
    except ValueError:
        errors.append("Informe uma data válida.")
    if not 2 <= len(name) <= 120:
        errors.append("O nome deve ter entre 2 e 120 caracteres.")
    if not 2 <= len(city) <= 80:
        errors.append("A cidade deve ter entre 2 e 80 caracteres.")
    if len(state) != 2 or not state.isalpha():
        errors.append("Use a sigla do estado com 2 letras.")
    if safe_url(registration_url) is None:
        errors.append("O link de inscrição deve começar com http:// ou https://.")
    if safe_url(photos_url) is None:
        errors.append("O link das fotos deve começar com http:// ou https://.")
    if status not in ("publicado", "rascunho"):
        errors.append("Selecione um status válido.")
    return (event_date, name, city, state, registration_url, photos_url, status), errors


def get_event_or_404(event_id):
    from flask import abort
    event = get_db().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if event is None:
        abort(404)
    return event


SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT NOT NULL,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL CHECK(length(state) = 2),
    registration_url TEXT NOT NULL DEFAULT '',
    photos_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('publicado', 'rascunho')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_public_date ON events(status, event_date);
"""


def init_database(seed=True):
    db = get_db()
    db.executescript(SCHEMA)
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        raise click.ClickException("Defina ADMIN_PASSWORD antes de inicializar o banco.")
    db.execute(
        "INSERT OR IGNORE INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")),
    )
    if seed and db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        today = date.today()
        samples = [
            (today + timedelta(days=3), "Joinville Night Run", "Joinville", "SC", "https://example.com/inscricao", "", "publicado"),
            (today + timedelta(days=11), "Circuito das Águas", "Blumenau", "SC", "https://example.com/circuito", "", "publicado"),
            (today - timedelta(days=4), "Desafio da Cidade", "Curitiba", "PR", "", "https://example.com/fotos", "publicado"),
            (today + timedelta(days=25), "Meia Maratona do Litoral", "Itajaí", "SC", "", "", "rascunho"),
        ]
        now = datetime.now().isoformat(timespec="seconds")
        db.executemany(
            """INSERT INTO events (event_date,name,city,state,registration_url,photos_url,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(d.isoformat(), n, c, s, i, p, st, now, now) for d, n, c, s, i, p, st in samples],
        )
    db.commit()
    db.execute("PRAGMA optimize")


@click.command("init-db")
@click.option("--sem-exemplos", is_flag=True, help="Cria o banco sem corridas fictícias.")
def init_db_command(sem_exemplos):
    init_database(seed=not sem_exemplos)
    click.echo("Banco inicializado com sucesso.")


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
