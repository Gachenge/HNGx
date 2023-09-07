from flask import Flask, request, jsonify
import datetime
import pytz


app = Flask(__name__)

@app.route('/api')
def getInfo():
    response = {
        "name": request.args.get('slack_name'),
        "track": request.args.get('track'),
        "day": datetime.datetime.now(pytz.UTC).strftime('%A'),
        "time": datetime.datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "gitfile": "https://github.com/Gachenge/HNGx/endpoint",
        "gitrepo": "https://github.com/Gachenge/HNGx",
        "status": 200
    }
    for key, val in response.items():
        if val is None:
            raise Exception(f"{key} must be entered")

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
