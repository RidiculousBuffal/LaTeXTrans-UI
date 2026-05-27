from backend.app.main import app


def test_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/healthz" in paths
    assert "/api/tasks" in paths
    assert "/api/tasks/upload" in paths
    assert "/api/tasks/pdf" in paths
    assert "/api/tasks/failures/summary" in paths


def test_frontend_static_routes_register_when_dist_exists() -> None:
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/{full_path:path}" in paths
