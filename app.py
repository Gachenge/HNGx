from flask import Flask, request, jsonify
from pathlib import Path
import os
import whisper
import subprocess
from flask_cors import CORS
import pika

app = Flask(__name__)
CORS(app)

DESKTOP_PATH = Path.home() / "Desktop"
FOLDER_NAME = "chrome_videos"
FOLDER_PATH = DESKTOP_PATH / FOLDER_NAME
FOLDER_PATH.mkdir(parents=True, exist_ok=True)

RABBITMQ_HOST = "localhost"
QUEUE_NAME = "transcription_tasks"

@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No video file supplied"}), 400
        file = request.files["file"]
        file_path = FOLDER_PATH / file.filename
        file.save(file_path)

        send_task_to_queue(file_path)
        print("task enqued")

        return jsonify({
            "video": f"{file.filename} saved successfully to chrome_videos folder on your desktop",
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/videos", methods=["GET"])
def get_folder_contents():
    contents = os.listdir(FOLDER_PATH)
    if len(contents) == 0:
        return jsonify({"message": "No recordings found"}), 204
    else:
        return jsonify({"folder_contents": contents})

def send_task_to_queue(video_path):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        print("channel added")

        message_body = str(video_path)
        channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=message_body, properties=pika.BasicProperties(delivery_mode=2))

        connection.close()

    except Exception as e:
       return jsonify({"Error": str(e)})


@app.route("/api/play/<video_name>", methods=["GET"])
def play_video(video_name):
    video_path = FOLDER_PATH / video_name
    if not video_path.is_file():
        return jsonify({"error": "Video not found"}), 404

    transcription_file_path = video_path.parent / f"{video_path.stem}.srt"

    return jsonify({"video_path": str(video_path), "transcription_path": str(transcription_file_path)}), 200


if __name__ == "__main__":
    app.run(debug=True)
