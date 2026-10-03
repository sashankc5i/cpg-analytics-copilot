from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import request_logging_middleware


def _app():
    app = FastAPI()
    app.middleware("http")(request_logging_middleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    return app


def test_request_id_is_generated_and_returned_in_header():
    client = TestClient(_app())

    response = client.get("/test")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) == 36


def test_each_request_gets_a_distinct_request_id():
    client = TestClient(_app())

    first = client.get("/test")
    second = client.get("/test")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
