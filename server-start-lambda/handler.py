import json
import boto3
def lambda_handler(event, context):
    # TODO implement
    ec2 = boto3.client('ec2')
    get_instance_response = ec2.describe_instances(Filters=[
        {
            'Name': 'tag:service',
            'Values': [
                'minecraft'
            ]
        }
    ])
    instance_id = get_instance_response['Reservations'][0]['Instances'][0]['InstanceId']
    ec2.start_instances(
        InstanceIds=[instance_id]
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
