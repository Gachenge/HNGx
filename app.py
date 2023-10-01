from flask import Flask, request, jsonify
from pathlib import Path
import os
import whisper
import subprocess
from flask_cors import CORS
import pika
import uuid
import datetime

app = Flask(__name__)
CORS(app)

DESKTOP_PATH = Path.home() / "Desktop"
FOLDER_NAME = "chrome_videos"
FOLDER_PATH = DESKTOP_PATH / FOLDER_NAME
FOLDER_PATH.mkdir(parents=True, exist_ok=True)

QUEUE_NAME = "transcription_tasks"
VIDEO_UPLOAD_URL_PREFIX = "https://chrome-extension-api-k5qy.onrender.com"

@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No video file supplied"}), 400
        file = request.files["file"]

        # Generate a unique video ID
        unique_video_id = str(uuid.uuid4())

        # Get the current date and time
        date_created = datetime.datetime.now().isoformat()

        # Construct the video name and file path
        video_name = f"{unique_video_id}_{file.filename}"
        file_path = FOLDER_PATH / video_name
        file.save(file_path)

        send_task_to_queue(file_path)

        # Construct the video URL
        video_url = f"{VIDEO_UPLOAD_URL_PREFIX}{video_name}"

        # Create a dictionary with video information
        video_info = {
            "id": unique_video_id,
            "video_url": video_url,
            "video_name": str(video_name),  # Convert PosixPath to string
            "date_created": date_created
        }

        return jsonify({
            "video": f"{file.filename} saved successfully to chrome_videos folder on your desktop",
            "video_info": video_info
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/videos", methods=["GET"])
def get_folder_contents():
    contents = os.listdir(FOLDER_PATH)
    non_transcript_files = [content for content in contents if not content.endswith(".srt")]

    if len(non_transcript_files) == 0:
        return jsonify({"message": "No video recordings found"}), 204
    else:
        return jsonify({"folder_contents": non_transcript_files})


def send_task_to_queue(video_path):
    try:
        # Get RabbitMQ connection parameters from environment variables
        rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        rabbitmq_user = os.environ.get('RABBITMQ_DEFAULT_USER', 'rabbitmq')
        rabbitmq_password = os.environ.get('RABBITMQ_DEFAULT_PASS', 'password')

        # Create a connection to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbitmq_host,
                credentials=pika.PlainCredentials(rabbitmq_user, rabbitmq_password),
            )
        )
        channel = connection.channel()

        # Declare the queue
        QUEUE_NAME = "transcription_tasks"
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        message_body = str(video_path)
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()

    except Exception as e:
        return jsonify({"Error": str(e)})


@app.route("/api/play/<video_name>", methods=["GET"])
def play_video(video_name):
    video_path = FOLDER_PATH / video_name
    if not video_path.is_file():
        return jsonify({"error": "Video not found"}), 404

    transcription_file_path = video_path.parent / f"{video_path.stem}.srt"

    return jsonify({"video_path": str(video_path), "transcripts": str(transcription_file_path)}), 200


if __name__ == "__main__":
    app.run(debug=True)
