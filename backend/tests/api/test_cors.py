PREFIX = "/api/v1/auth/login"


def preflight(client, origin):
    # what a browser sends first, to ask whether a page from this origin may call the API
    return client.options(
        PREFIX,
        headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )


def test_the_frontend_may_call_the_api(client):
    res = preflight(client, "http://localhost:3000")

    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_another_site_may_not(client):
    res = preflight(client, "https://evil.example.com")

    assert res.status_code == 400
    assert "access-control-allow-origin" not in res.headers
