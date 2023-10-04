from flask import Flask, request, jsonify, send_file, send_from_directory
from pathlib import Path
import os
import whisper
import subprocess
from flask_cors import CORS
import pika
import uuid
import datetime
import json
import time
from worker import worker_main
from multiprocessing import Process
from config import STATIC_FOLDER, QUEUE_NAME, RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASSWORD


app = Flask(__name__)
CORS(app)

os.makedirs(STATIC_FOLDER, exist_ok=True)

VIDEO_UPLOAD_URL_PREFIX = "https://chrome-extension-api-k5qy.onrender.com"


def send_task_to_queue(video_path):
    try:
        parameters = pika.URLParameters(f"amqps://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}")
        connection = pika.BlockingConnection(parameters)

        channel = connection.channel()

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
        return {"error": str(e)}

@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No video file supplied"}), 400
        file = request.files["file"]
        
        unique_video_id = str(uuid.uuid4())

        date_created = datetime.datetime.now().isoformat()

        video_name = file.filename
        file_path = os.path.join(STATIC_FOLDER, video_name)
        file.save(file_path)

        send_task_to_queue(file_path)

        response_data = {
            "id": unique_video_id,
            "video_name": file.filename,
            "created_at": date_created,
            "video_info": "Video created successfull and processing task queued"
        }

        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")

        return response, 200
    except Exception as e:
        error_response = {"error": str(e)}
        return jsonify(error_response), 500

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

        parent_directory = os.path.dirname(video_path)

        transcript_file_path = os.path.join(parent_directory, f"{os.path.splitext(os.path.basename(video_path))[0]}.srt")
        with open(transcript_file_path, "w") as f:
            f.write(result["text"])

        return transcript_file_path

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}
    finally:
        time.sleep(5)
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)

@app.route("/api/videos", methods=["GET"])
def get_folder_contents():
    contents = os.listdir(STATIC_FOLDER)
    non_transcript_files = [content for content in contents if not content.endswith(".srt")]

    if len(non_transcript_files) == 0:
        return jsonify({"message": "No video recordings found"}), 204
    else:
        return jsonify({"folder_contents": non_transcript_files})

@app.route("/api/play/<video_name>", methods=["GET"])
def serve_video(video_name):
    video_path = os.path.join(STATIC_FOLDER, video_name)
    srt_path = os.path.join(STATIC_FOLDER, f"{os.path.splitext(video_name)[0]}.srt")

    if not os.path.isfile(video_path):
        return jsonify({"error": "Video not found"}), 404
    if not os.path.isfile(srt_path):
        return jsonify({"error": "Transcribed text not found"}), 404

    response = send_file(
        video_path,
        as_attachment=True,
        download_name=f"{video_name}.mp4",
        mimetype="video/mp4",
    )

    response.headers["X-SRT-File"] = srt_path
    return response

if __name__ == "__main__":
    flask_process = Process(target=app.run, kwargs={"debug": True})
    flask_process.start()

    worker_process = Process(target=worker_main)
    worker_process.start()

    flask_process.join()
    worker_process.join()
