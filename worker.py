import pika
import subprocess
import os
import whisper

STATIC_FOLDER = os.path.join(os.getcwd(), "static")

# RabbitMQ connection parameters
rabbitmq_host = os.getenv("RABBITMQ_HOST")
rabbitmq_user = os.getenv("RABBITMQ_USER")
rabbitmq_password = os.getenv("RABBITMQ_PASSWORD")

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

        newName = video_path.split('.')[0]+".srt"

        transcription_file_path =  os.path.join(STATIC_FOLDER, newName) 
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        return transcription_file_path

    except subprocess.CalledProcessError as e:
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
