def test_health_check(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"code": 0, "message": "ok", "data": {"status": "ok", "app": "LIMS"}}
