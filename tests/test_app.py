from io import BytesIO
from app import calculate_stats, get_db, parse_time, athlete_analysis

def test_time_formats():
    assert parse_time("47:18") == 2838
    assert parse_time("01:02:03") == 3723
    assert parse_time("DNF") is None

def test_stats_math():
    rows = [{"net_seconds": s, "gross_seconds": None, "status": "FINISHED", "sex": "M" if i < 3 else "F", "category": "A"} for i, s in enumerate([2400, 2700, 3000, 3300])]
    stats = calculate_stats(rows, 10)
    assert stats["overall"]["count"] == 4
    assert stats["overall"]["best"] == 2400
    assert stats["overall"]["mean"] == 2850
    assert stats["overall"]["median"] == 2850
    assert stats["overall"]["p50"] == 2850
    assert stats["by_sex"]["M"]["count"] == 3

def test_public_and_admin_regression(client, logged):
    assert client.get("/").status_code == 200
    assert b"Prova Teste" in client.get("/").data
    assert logged.get("/admin").status_code == 200

def test_csv_import_multiple_distances(app, logged):
    content = "Atleta;Numero;Sexo;Categoria;Distancia;Tempo Liquido;Status\nAna;10;F;F30;5 km;24:00;Concluiu\nBia;11;F;F30;10 km;00:49:00;Concluiu\nCaio;12;M;M30;5 km;DNF;DNF\n".encode()
    response = logged.post("/admin/eventos/1/resultados/importar", data={"file": (BytesIO(content), "resultados.csv")}, content_type="multipart/form-data")
    assert response.status_code == 302
    mapping = response.headers["Location"]
    assert b"Conferir colunas" in logged.get(mapping).data
    response = logged.post(mapping, data={"name": "Atleta", "bib": "Numero", "sex": "Sexo", "category": "Categoria", "distance": "Distancia", "net_time": "Tempo Liquido", "status": "Status"})
    assert b"Concluintes" in response.data
    token = mapping.split("/admin/resultados/mapear/")[1]
    assert logged.post(f"/admin/resultados/confirmar/{token}", data={"replace": "1"}).status_code == 302
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM distances").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM results WHERE status='FINISHED'").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM results WHERE status='DNF'").fetchone()[0] == 1
    assert logged.get("/resultados/prova-teste").status_code == 200

def test_athlete_percent_and_pace(app):
    with app.app_context():
        db = get_db()
        did = db.execute("INSERT INTO distances(event_id,label,distance_km) VALUES(1,'10 km',10)").lastrowid
        for i, t in enumerate([2400, 2700, 3000, 3300], 1):
            db.execute("INSERT INTO results(event_id,distance_id,bib,name,sex,category,net_seconds,status,imported_at) VALUES(1,?,?,?,?,?,?,?,?)", (did, str(i), f'A{i}', "M", "M30", t, "FINISHED", "now"))
        db.commit()
        athlete = db.execute("SELECT r.*,d.distance_km FROM results r JOIN distances d ON d.id=r.distance_id WHERE r.name='A2'").fetchone()
        rows = db.execute("SELECT * FROM results WHERE distance_id=?", (did,)).fetchall()
        analysis = athlete_analysis(athlete, rows)
        assert analysis["pace"] == 270
        assert analysis["overall"]["place"] == 2
        assert analysis["overall"]["top"] == 50.0
