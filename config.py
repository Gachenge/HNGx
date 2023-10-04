import os
from dotenv import load_dotenv

load_dotenv(".env")

STATIC_FOLDER = os.path.join(os.getcwd(), "static")

QUEUE_NAME = "transcription_tasks"

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD')
