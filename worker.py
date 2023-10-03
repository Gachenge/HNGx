import pika
import subprocess
import os
import whisper
import time
from config import STATIC_FOLDER, QUEUE_NAME, RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASSWORD

# Maximum number of retries for each exception type
MAX_RETRIES = 1

def worker_main():
    
    while True:
        try:
            parameters = pika.URLParameters(f"amqps://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(queue=QUEUE_NAME, durable=True)

            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

            print('Waiting for transcription tasks. To exit, press CTRL+C')
            channel.start_consuming()

        except pika.exceptions.StreamLostError:
            print('Stream connection lost. Reconnecting in 5 seconds...')
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")

def callback(ch, method, properties, body):
    try:
        video_path = body.decode()
        converted_video_path = "converted_video.mp4"

        retry_count = 0

        while retry_count <= MAX_RETRIES:
            try:
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-i", str(video_path),
                    "-acodec", "libmp3lame",
                    "-ab", "192k",
                    "-ar", "44100",
                    converted_video_path
                ]

                subprocess.run(ffmpeg_cmd, check=True)
                model = whisper.load_model("base")
                result = model.transcribe(converted_video_path)

                newName = video_path.split('.')[0]+".srt"

                transcription_file_path = os.path.join(STATIC_FOLDER, newName) 
                with open(transcription_file_path, "w") as f:
                    f.write(result["text"])

                ch.basic_ack(delivery_tag=method.delivery_tag)
                break  # Success, break out of retry loop

            except subprocess.CalledProcessError as e:
                print(f"FFmpeg error: {e}")
                retry_count += 1

            except FileNotFoundError as e:
                print(f"File not found error: {e}")
                retry_count += 1

            except whisper.exceptions.WhisperException as e:
                print(f"Whisper error: {e}")
                retry_count += 1

            except Exception as e:
                print(f"Error processing message: {e}")
                retry_count += 1
    
    finally:
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)

if __name__ == "__main__":
    worker_main()
