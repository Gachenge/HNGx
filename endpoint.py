from flask import Flask, request, jsonify
import datetime
import pytz


app = Flask(__name__)


@app.route('/api')
def getInfo():
    response = {
        "slack_name": request.args.get('slack_name'),
        "current_day": datetime.datetime.now(pytz.UTC)
                                        .strftime('%A'),
        "utc_time": datetime.datetime.now(pytz.UTC)
                                        .strftime('%Y-%m-%dT%H:%M:%SZ'),
        "track": request.args.get('track'),
        "github_file_url":
            "https://github.com/Gachenge/HNGx/blob/main/endpoint.py",
        "github_repo_url": "https://github.com/Gachenge/HNGx",
        "status": 200
    }
    for key, val in response.items():
        if val is None:
            raise Exception(f"{key} must be entered")

    return jsonify(response)
