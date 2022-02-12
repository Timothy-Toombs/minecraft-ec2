from flask import Flask, jsonify

app = Flask(__name__)

health_status = True

@app.route('/health')
def health():
    resp = jsonify(health="healthy")
    resp.status_code = 200
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)