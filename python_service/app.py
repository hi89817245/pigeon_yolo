from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

FROZEN = getattr(sys, "frozen", False)
APP_ROOT = (
    Path(sys.executable).resolve().parent
    if FROZEN
    else Path(__file__).resolve().parents[1]
)
if not FROZEN and str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from project.core.iris_pipeline import IrisPipeline


SERVICE_PORT = int(os.environ.get("PYTHON_SERVICE_PORT", "8001"))


def resolve_models_dir() -> Path:
    env_dir = os.environ.get("PIGEON_MODELS_DIR")
    if env_dir:
        return Path(env_dir)

    app_models = APP_ROOT / "models"
    if app_models.exists():
        return app_models

    return APP_ROOT / "project" / "assets"


MODELS_DIR = resolve_models_dir()
UPLOAD_DIR = APP_ROOT / "uploads" / "python_service"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
pipeline = IrisPipeline(
    project_dir=APP_ROOT / "project",
    assets_dir=MODELS_DIR,
    crop_dir=APP_ROOT / "tmp" / "crops",
)


def save_upload(file_storage):
    filename = f"{uuid.uuid4().hex}.jpg"
    path = UPLOAD_DIR / filename
    file_storage.save(str(path))
    return str(path)


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/compare")
def compare():
    f1 = request.files.get("img1")
    f2 = request.files.get("img2")
    if not f1 or not f2:
        return jsonify({"error": "need two images"}), 400

    p1 = save_upload(f1)
    p2 = save_upload(f2)
    result = pipeline.compare(p1, p2)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result)


@app.post("/search")
def search():
    f = request.files.get("image")
    k = int(request.form.get("k", 5))
    if not f:
        return jsonify({"error": "need image"}), 400

    p = save_upload(f)
    result = pipeline.search(p, k)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result)


@app.post("/embed")
def embed():
    f = request.files.get("image")
    if not f:
        return jsonify({"error": "need image"}), 400

    p = save_upload(f)
    result = pipeline.embed(p)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result)


@app.get("/image")
def image():
    path = request.args.get("path")
    if not path:
        abort(400)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=SERVICE_PORT, debug=False)
