from app import app


def test_fastapi_app_title_and_routes():
    assert app.title == "PytestDeck Core API"
    assert app.version == "0.1.0"
    assert len(app.routes) >= 5
