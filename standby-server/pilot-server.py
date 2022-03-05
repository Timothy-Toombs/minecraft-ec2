import boto3
from flask import Flask, jsonify
import requests
START_FXN_NAME='minecraft-server-start'
app = Flask(__name__)
lambda_client = boto3.client('lambda', region_name='us-west-2')

@app.route('/status')
def status():
    try:
        r = requests.get('minecraft.timpai.com:8080/health')
        response = jsonify(status="started")
    except:
        lambda_client.invoke(FunctionName=START_FXN_NAME)
        response = jsonify(status="starting")
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)