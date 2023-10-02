import pika
import subprocess
import os
import whisper
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv(".env")

STATIC_FOLDER = os.path.join(os.getcwd(), "static")

# RabbitMQ connection parameters
rabbitmq_host = os.environ.get('RABBITMQ_HOST')
rabbitmq_user = os.environ.get('RABBITMQ_USER')
rabbitmq_password = os.environ.get('RABBITMQ_PASSWORD')

QUEUE_NAME = "transcription_tasks"

app = Flask(__name__)

def callback(ch, method, properties, body):
    video_path = body.decode()
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

        transcription_file_path = os.path.join(STATIC_FOLDER, f"{video_path.stem}.srt")
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        with app.app_context():
            return jsonify({"error": f"FFmpeg error: {e}"})

    except subprocess.CalledProcessError as e:
        with app.app_context():
            return jsonify({"error": f"FFmpeg error: {e}"})
    finally:
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)

parameters = pika.URLParameters(f"amqps://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}")
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME, durable=True)

# Set up a consumer
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

print('Waiting for transcription tasks. To exit, press CTRL+C')
channel.start_consuming()
