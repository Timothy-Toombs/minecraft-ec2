import socket
import boto3
START_FXN_NAME='minecraft-server-start'
host = ''
port = 25565
backlog = 5
size = 1024
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host,port))
s.listen(backlog)
lambda_client = boto3.client('lambda', region_name='us-west-2')
while 1:
    client, address = s.accept()
    data = client.recv(size)
    print("received request from client:")
    print(data)
    print("\n\n")
    if data:
        client.send(data)

    response = lambda_client.invoke(FunctionName=START_FXN_NAME)
    print(response)
    client.close()