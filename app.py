from flask import Flask, request, jsonify
from pathlib import Path
import os
import whisper
import subprocess
from flask_cors import CORS
import pika
import uuid
import datetime
import json

app = Flask(__name__)
CORS(app)

DESKTOP_PATH = Path.home() / "Desktop"
FOLDER_NAME = "chrome_videos"
FOLDER_PATH = DESKTOP_PATH / FOLDER_NAME
FOLDER_PATH.mkdir(parents=True, exist_ok=True)

QUEUE_NAME = "transcription_tasks"
VIDEO_UPLOAD_URL_PREFIX = "https://chrome-extension-api-k5qy.onrender.com"

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_USER = os.environ.get('RABBITMQ_DEFAULT_USER', 'rabbitmq')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_DEFAULT_PASS', 'password')


def send_task_to_queue(video_path):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD),
            )
        )
        channel = connection.channel()

        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        unique_video_id = str(uuid.uuid4())

        date_created = datetime.datetime.now().isoformat()

        video_name = f"{unique_video_id}_{video_path.name}"

        video_url = f"{VIDEO_UPLOAD_URL_PREFIX}/{video_name}"

        video_info = {
            "id": unique_video_id,
            "video_url": video_url,
            "video_name": str(video_name),
            "date_created": date_created
        }

        video_info_json = json.dumps(video_info)

        message_body = {
            "video_path": str(video_path),
            "video_info": video_info_json 
        }
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(message_body),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()

        # Return video_info dictionary
        return video_info

    except Exception as e:
        return jsonify({"Error": str(e)})

@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No video file supplied"}), 400
        file = request.files["file"]
        file_path = FOLDER_PATH / file.filename
        file.save(file_path)

        # Get the video_info from send_task_to_queue
        video_info = send_task_to_queue(file_path)

        response_data = {
            "video": "video saved successfully to chrome_videos folder on your desktop",
        }

        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")

        return response, 200
    except Exception as e:
        error_response = {"error": str(e)}
        return jsonify(error_response), 500


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
        rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        rabbitmq_user = os.environ.get('RABBITMQ_DEFAULT_USER', 'rabbitmq')
        rabbitmq_password = os.environ.get('RABBITMQ_DEFAULT_PASS', 'password')

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbitmq_host,
                credentials=pika.PlainCredentials(rabbitmq_user, rabbitmq_password),
            )
        )
        channel = connection.channel()

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

def generate_transcript(video_path):
    converted_video_path = "converted_video.mp4"

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-ar", "44100",
        converted_video_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        model = whisper.load_model("base")
        result = model.transcribe(converted_video_path)

        transcription_file_path = video_path.parent / f"{video_path.stem}.srt"
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        return transcription_file_path

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg error: {e}"})
    finally:
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)

@app.route("/api/play/<video_name>", methods=["GET"])
def play_video(video_name):
    video_path = FOLDER_PATH / video_name
    if not video_path.is_file():
        return jsonify({"error": "Video not found"}), 404

    transcription_file_path = video_path.parent / f"{video_path.stem}.srt"

    return jsonify({"video_path": str(video_path), "transcripts": str(transcription_file_path)}), 200


if __name__ == "__main__":
    app.run(debug=True)
