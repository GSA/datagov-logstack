import json
import time
import pytest
import requests


LOGSTASH_HTTP_URL = 'http://logstash:8080'
LOGSTASH_AUTH = ('logstash', 'logstash')
LOCALSTACK_ENDPOINT = 'http://localstack:4566'
S3_BUCKET = 'logstash-bucket'


@pytest.fixture
def s3_client():
    """Create boto3 S3 client pointing to LocalStack."""
    import boto3

    return boto3.client(
        's3',
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )


def send_log_event(message):
    """
    Send a log message to Logstash HTTP input.

    Args:
        message: Log message string (syslog format)

    Returns:
        requests.Response object
    """
    response = requests.post(
        LOGSTASH_HTTP_URL,
        auth=LOGSTASH_AUTH,
        data=message,
        headers={'Content-Type': 'text/plain'}
    )
    return response


def wait_for_s3_objects(s3_client, bucket, min_count=1, timeout=30):
    """
    Wait for S3 objects to appear in bucket.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        min_count: Minimum number of objects to wait for
        timeout: Maximum seconds to wait

    Returns:
        List of S3 object keys
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = s3_client.list_objects_v2(Bucket=bucket)
            if response.get('KeyCount', 0) >= min_count:
                return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception:
            pass

        time.sleep(1)

    return []


def get_s3_log_events(s3_client, bucket):
    """
    Retrieve all log events from S3 bucket.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name

    Returns:
        List of parsed log event dicts
    """
    events = []

    try:
        response = s3_client.list_objects_v2(Bucket=bucket)

        for obj in response.get('Contents', []):
            obj_response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
            content = obj_response['Body'].read().decode('utf-8')

            for line in content.strip().split('\n'):
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    return events


def clear_s3_bucket(s3_client, bucket):
    """
    Delete all objects from S3 bucket.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
    """
    try:
        response = s3_client.list_objects_v2(Bucket=bucket)

        for obj in response.get('Contents', []):
            s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
    except Exception:
        pass
