# Philip Thompson 22024226
import os
import sys
import uuid

from flask import Flask, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")

sys.path.append(SRC_DIR)

from predict_and_grade import run_pipeline, load_trained_model  # noqa: E402

app = Flask(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

os.makedirs(TEMP_DIR, exist_ok=True)

model = load_trained_model()


def is_allowed_file(filename):
    _, extension = os.path.splitext(filename.lower())
    return extension in ALLOWED_EXTENSIONS


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    if not file or file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not is_allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    _, extension = os.path.splitext(file.filename.lower())
    safe_filename = f"{uuid.uuid4().hex}{extension}"
    temp_path = os.path.join(TEMP_DIR, safe_filename)

    try:
        file.save(temp_path)
        result = run_pipeline(temp_path, model=model)
        return jsonify(result)

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)