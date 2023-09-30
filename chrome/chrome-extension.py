from flask import Flask, request, jsonify, send_file
import shutil
from pathlib import Path
import os
import whisper
import subprocess

app = Flask(__name__)

DESKTOP_PATH = Path.home() / "Desktop"
FOLDER_NAME = "chrome_videos"
FOLDER_PATH = DESKTOP_PATH / FOLDER_NAME
FOLDER_PATH.mkdir(parents=True, exist_ok=True)


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No video file supplied"}), 400
    file = request.files["file"]
    file_path = FOLDER_PATH / file.filename
    file.save(file_path)

    # Generate the transcript for the uploaded video and save it
    transcription_file_path = generate_transcript(file_path)

    return jsonify({
        "video": f"{file.filename} saved successfully to chrome_videos folder on your desktop",
        "transcription_path": str(transcription_file_path)
    }), 200


@app.route("/api/videos", methods=["GET"])
def get_folder_contents():
    contents = os.listdir(FOLDER_PATH)
    if len(contents) == 0:
        return jsonify({"message": "No recordings found"}), 204
    else:
        return jsonify({"folder_contents": contents})


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
        return jsonify({"error": f"FFmpeg error: {e}"})
    finally:
        if os.path.exists(converted_video_path):
            os.remove(converted_video_path)


@app.route("/api/play/<video_name>", methods=["GET"])
def play_video(video_name):
    video_path = FOLDER_PATH / video_name
    if not video_path.is_file():
        return jsonify({"error": "Video not found"}), 404

    # Construct the transcript file path based on the video name
    transcription_file_path = video_path.parent / f"{video_path.stem}.srt"

    # Return the video along with the transcript file path
    return jsonify({"video_path": str(video_path), "transcription_path": str(transcription_file_path)}), 200


if __name__ == "__main__":
    app.run(debug=True)
