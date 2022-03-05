from flask import Flask, jsonify

app = Flask(__name__)

health_status = True

@app.route('/health')
def health():
    resp = jsonify(health="healthy")
    resp.status_code = 200
    return resp

@app.route('/status')
def status():
    response = jsonify(status="started")
    response.status_code = 200
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)