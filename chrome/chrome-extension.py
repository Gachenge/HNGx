from flask import Flask, request, jsonify, send_file
import shutil
from pathlib import Path
import os

app = Flask(__name__)

DESKTOP_PATH = Path.home() / "Desktop"

FOLDER_NAME = "chrome_videos"

FOLDER_PATH = DESKTOP_PATH / FOLDER_NAME
FOLDER_PATH.mkdir(parents=True, exist_ok=True)


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No video file supplied"}), 400

    file = request.files["file"]

    file_path = FOLDER_PATH / file.filename

    file.save(file_path)

    return jsonify({"message": f"{file.filename} saved successfully to chrome_videos folder on your desktop"}), 200


@app.route("/api/videos", methods=["GET"])
def get_folder_contents():
    contents = os.listdir(FOLDER_PATH)

    if len(contents) == 0:
        return jsonify({"message": "No recordings found"}), 204
    else:
        return jsonify({"folder_contents": contents})


@app.route("/api/play/<video_name>", methods=["GET"])
def play_video(video_name):
    video_path = FOLDER_PATH / video_name

    if not video_path.is_file():
        return jsonify({"error": "Video not found"}), 404

    return send_file(video_path), 200


if __name__ == "__main__":
    app.run(debug=True)
