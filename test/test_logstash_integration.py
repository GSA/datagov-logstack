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


class TestRouterLogParsing:
    """Integration tests for Cloud Foundry Router log parsing."""

    def test_router_log_basic_parsing(self, s3_client):
        """Test router log extracts basic HTTP request fields."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [RTR/0] - '
            '[tags@47450 app="catalog" source_type="RTR" instance_id="0" '
            'ip="10.10.1.5" organization_id="org-123" organization_name="gsa-datagov" '
            'space_id="space-456" space_name="prod"] '
            'catalog-prod.data.gov - [2026-11-13T20:00:00.123456789Z] '
            '"GET /dataset/water-quality HTTP/1.1" 200 0 21445 "-" '
            '"Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "127.0.0.1:54321" '
            '"10.10.2.10:8080" x_forwarded_for:"203.0.113.42, 64.252.66.100, 127.0.0.1" '
            'x_forwarded_proto:"https" vcap_request_id:"req-abc-123" '
            'response_time:0.023 gorouter_time:0.001 app_id:"app-789" app_index:"0"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        keys = wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        assert len(keys) > 0

        events = get_s3_log_events(s3_client, S3_BUCKET)
        assert len(events) > 0

        event = events[0]
        assert event['hostname'] == 'catalog-prod.data.gov'
        assert event['http_method'] == 'GET'
        assert event['request'] == '/dataset/water-quality'
        assert event['http_version'] == 'HTTP/1.1'
        assert event['status'] == 200
        assert 'timestamp' in event

    def test_router_log_real_ip_extraction(self, s3_client):
        """Test router log extracts real client IP from X-Forwarded-For."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [RTR/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'catalog-prod.data.gov - [2026-11-13T20:00:00.123456789Z] '
            '"GET /dataset/test HTTP/1.1" 200 0 1000 "-" "curl/7.0" '
            '"127.0.0.1:54321" "10.10.2.10:8080" '
            'x_forwarded_for:"203.0.113.42, 10.0.0.5, 127.0.0.1" '
            'x_forwarded_proto:"https"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['real_ip'] == '203.0.113.42'
        assert '10.0.0.5' not in event.get('forwarded_ips', '')
        assert '127.0.0.1' not in event.get('forwarded_ips', '')

    def test_router_log_skips_all_internal_ips(self, s3_client):
        """Test router log IP extraction when all IPs are internal."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [RTR/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'catalog-prod.data.gov - [2026-11-13T20:00:00.123456789Z] '
            '"GET /dataset/test HTTP/1.1" 200 0 1000 "-" "curl/7.0" '
            '"127.0.0.1:54321" "10.10.2.10:8080" '
            'x_forwarded_for:"10.0.0.5, 192.168.1.10, 127.0.0.1" '
            'x_forwarded_proto:"https"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['real_ip'] == '10.0.0.5'


class TestApplicationLogParsing:
    """Integration tests for CKAN application log parsing."""

    def test_ckan_log_basic_parsing(self, s3_client):
        """Test CKAN log extracts timestamp, level, logger, status, path, render time."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            '2026-11-13 20:00:00,123 INFO  [ckan.config.middleware.flask_app]  '
            '200 /dataset/water-quality render time 0.045 seconds'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['log_level'] == 'INFO'
        assert event['logger'] == 'ckan.config.middleware.flask_app'
        assert event['status'] == 200
        assert event['request_path'] == '/dataset/water-quality'
        assert event['render_time'] == 0.045

    def test_ckan_log_error_status(self, s3_client):
        """Test CKAN log with 404 status."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            '2026-11-13 20:00:00,123 INFO  [ckan.config.middleware.flask_app]  '
            '404 /dataset/nonexistent render time 0.012 seconds'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['status'] == 404
        assert event['request_path'] == '/dataset/nonexistent'


class TestWAFLogParsing:
    """Integration tests for WAF Nginx log parsing."""

    def test_waf_log_bot_detection(self, s3_client):
        """Test WAF log with bot detection extracts all fields."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'NginxLog "GET /dataset/123 HTTP/1.1" 429 456 "bot-detection"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['http_method'] == 'GET'
        assert event['request'] == '/dataset/123'
        assert event['request_path'] == '/dataset/123'
        assert event['http_version'] == 'HTTP/1.1'
        assert event['status'] == 429
        assert event['nginx_bytes_sent'] == 456
        assert event['waf_detection'] == 'bot-detection'

    def test_waf_log_rate_limit(self, s3_client):
        """Test WAF log with rate-limit detection."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'NginxLog "POST /api/action/package_search HTTP/2.0" 429 0 "rate-limit"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['http_method'] == 'POST'
        assert event['request_path'] == '/api/action/package_search'
        assert event['waf_detection'] == 'rate-limit'

    def test_waf_log_query_string_preserved(self, s3_client):
        """Test WAF log preserves query string separately from path."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'NginxLog "GET /dataset/search?q=water&page=2 HTTP/1.1" 429 100 "query-permutation"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert event['request'] == '/dataset/search?q=water&page=2'
        assert event['request_path'] == '/dataset/search'
        assert event['waf_detection'] == 'query-permutation'


class TestDropFilters:
    """Integration tests for Logstash drop filters."""

    def test_drop_waf_log_without_detection(self, s3_client):
        """Test WAF logs without detection (dash) are dropped."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'NginxLog "GET /dataset/123 HTTP/1.1" 200 321 "-"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        time.sleep(5)

        events = get_s3_log_events(s3_client, S3_BUCKET)
        assert len(events) == 0

    def test_drop_logstash_health_check(self, s3_client):
        """Test logstash health check logs (200 status) are dropped."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 logstash-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [RTR/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'logstash-prod.data.gov - [2026-11-13T20:00:00.123456789Z] '
            '"GET /health HTTP/1.1" 200 0 50 "-" "CloudFoundry" '
            '"127.0.0.1:54321" "10.10.2.10:8080" '
            'x_forwarded_for:"127.0.0.1" x_forwarded_proto:"http"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        time.sleep(5)

        events = get_s3_log_events(s3_client, S3_BUCKET)
        assert len(events) == 0

    def test_keep_waf_log_with_detection(self, s3_client):
        """Test WAF logs with detection are kept."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [APP/PROC/WEB/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'NginxLog "GET /dataset/123 HTTP/1.1" 429 456 "bot-detection"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        assert len(events) == 1
        assert events[0]['waf_detection'] == 'bot-detection'


class TestFieldRemoval:
    """Integration tests for field removal based on environment."""

    def test_production_removes_sensitive_fields(self, s3_client):
        """Test production environment removes log_data and raw_message_content."""
        clear_s3_bucket(s3_client, S3_BUCKET)

        log_message = (
            '<14>1 2026-11-13T20:00:00.000000+00:00 catalog-prod.data.gov '
            '01234567-89ab-cdef-0123-456789abcdef [RTR/0] - '
            '[tags@47450 instance_id="0" ip="10.10.1.5" space_name="prod"] '
            'catalog-prod.data.gov - [2026-11-13T20:00:00.123456789Z] '
            '"GET /dataset/test HTTP/1.1" 200 0 1000 "-" "curl/7.0" '
            '"127.0.0.1:54321" "10.10.2.10:8080" '
            'x_forwarded_for:"203.0.113.42" x_forwarded_proto:"https"'
        )

        response = send_log_event(log_message)
        assert response.status_code == 200

        wait_for_s3_objects(s3_client, S3_BUCKET, min_count=1, timeout=30)
        events = get_s3_log_events(s3_client, S3_BUCKET)

        event = events[0]
        assert 'log_data' not in event
        assert 'raw_message_content' not in event
        assert 'hostname' in event
        assert 'http_method' in event
