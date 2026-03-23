from flask import Flask, request, jsonify, send_from_directory, abort, send_file
import os, uuid, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from project.core.iris_pipeline import IrisPipeline

# ---------------- CONFIG ----------------
UPLOAD_DIR = BASE_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# ---------------------------------------

app = Flask(__name__)

pipeline = IrisPipeline(project_dir=BASE_DIR)


# -------- frontend --------
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR / "static"), "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(str(BASE_DIR / "static"), path)


# -------- api --------
def save_upload(file):
    fn = f"{uuid.uuid4().hex}.jpg"
    path = UPLOAD_DIR / fn
    file.save(str(path))
    return str(path)


@app.route("/compare", methods=["POST"])
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


@app.route("/search", methods=["POST"])
def search():
    f = request.files.get("image")
    k = int(request.form.get("k", 5))

    if not f:
        return jsonify({"error": "need image"}), 400

    p = save_upload(f)

    result = pipeline.search(p, k)
    if result.get("error"):
        return jsonify(result), 400

    for r in result["results"]:
        r["image"] = "/image?path=" + r["path"]

    result["query_crop"] = "/image?path=" + result["query_crop"]
    return jsonify(result)


@app.route("/embed", methods=["POST"])
def embed():
    f = request.files.get("image")
    if not f:
        return jsonify({"error": "need image"}), 400

    p = save_upload(f)
    result = pipeline.embed(p)
    if result.get("error"):
        return jsonify(result), 400

    result["query_crop"] = "/image?path=" + result["query_crop"]
    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/image")
def image():
    path = request.args.get("path")
    if path is None:
        abort(400)

    if not os.path.exists(path):
        abort(404)

    return send_file(path, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
