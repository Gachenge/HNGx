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

app = Flask(__name__)
CORS(app)

# Define the static folder path for storing video files
STATIC_FOLDER = os.path.join(os.getcwd(), "static")

# Ensure the static folder exists
os.makedirs(STATIC_FOLDER, exist_ok=True)

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
        
        # Generate a unique video ID
        unique_video_id = str(uuid.uuid4())

        # Get the current date and time
        date_created = datetime.datetime.now().isoformat()

        # Construct the video name and file path
        video_name = f"{unique_video_id}_{file.filename}"
        file_path = os.path.join(STATIC_FOLDER, video_name)
        file.save(file_path)

        # Generate the transcript for the uploaded video
        transcript_file = generate_transcript(file_path)

        # Enqueue transcription task
        video_info = send_task_to_queue(file_path)

        response_data = {
            "video": f"{file.filename} saved successfully to static folder",
            "video_info": video_info,
            "transcript": str(transcript_file)
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

        # Save the transcript to a text file in the same folder as the video
        transcription_file_path = video_path.parent / f"{video_path.stem}.srt"
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        return transcription_file_path  # Return the file path of the transcript

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}
    finally:
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

# Add routes for serving video files and transcripts if needed
@app.route("/static/<video_name>", methods=["GET"])
def serve_video(video_name):
    video_path = os.path.join(STATIC_FOLDER, video_name)
    if not os.path.isfile(video_path):
        return jsonify({"error": "Video not found"}), 404

    return send_file(video_path)

if __name__ == "__main__":
    app.run(debug=True)
