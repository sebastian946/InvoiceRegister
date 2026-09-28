from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import find_frontend_dir, mount_frontend


def build_frontend(folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text("<html><body>Invoice Register UI</body></html>")
    (folder / "assets").mkdir()
    (folder / "assets" / "app.js").write_text("console.log('ok')")
    return folder


def make_app(folder):
    application = FastAPI()

    @application.get("/Health")
    def health():
        return {"status": "healthy"}

    mounted = mount_frontend(application, folder)
    return TestClient(application), mounted


def test_finds_the_first_folder_with_an_index(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    built = build_frontend(tmp_path / "dist")

    assert find_frontend_dir([empty, built]) == built


def test_finds_nothing_when_no_frontend_is_built(tmp_path):
    assert find_frontend_dir([tmp_path / "missing"]) is None


def test_serves_the_index_and_its_assets(tmp_path):
    client, mounted = make_app(build_frontend(tmp_path / "dist"))

    assert mounted is True
    assert "Invoice Register UI" in client.get("/").text
    assert client.get("/assets/app.js").status_code == 200


def test_api_routes_win_over_the_frontend(tmp_path):
    client, _ = make_app(build_frontend(tmp_path / "dist"))

    response = client.get("/Health")

    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "healthy"}


def test_api_works_without_a_frontend():
    client, mounted = make_app(None)

    assert mounted is False
    assert client.get("/Health").status_code == 200
    assert client.get("/").status_code == 404
