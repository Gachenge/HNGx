import pika
import subprocess
import os
import whisper

# RabbitMQ connection parameters
RABBITMQ_HOST = os.environ.get('RABBIT_HOST', 'localhost')
RABBITMQ_USER = os.environ.get('RABBIT_USER', 'user')
RABBITMQ_PASSWORD = os.environ.get('RABBIT_PASS', 'password')
QUEUE_NAME = "transcription_tasks"

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

        transcription_file_path = video_path.parent / f"{video_path.stem}.srt"
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        return transcription_file_path

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg error: {e}"})
    finally:
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD),
    )
)
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME, durable=True)

# Set up a consumer
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

print('Waiting for transcription tasks. To exit, press CTRL+C')
channel.start_consuming()
