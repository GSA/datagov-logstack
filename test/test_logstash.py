import re
import unittest
from pathlib import Path

import requests


LOGSTASH_HEALTHCHECK = 'http://logstash:9600/?pretty'
LOGSTASH_CONFIG = Path(__file__).resolve().parents[1] / 'logstash' / 'logstash.conf'

class TestLogstash(unittest.TestCase):
  def test_anonymous_access_denied(self):
    response = requests.get('http://logstash:8080')
    assert response.status_code == 401

  def test_authorized_user_allowed(self):
    client = requests.Session()
    client.auth = ('logstash', 'logstash')

    response = client.get('http://logstash:8080')
    assert response.status_code == 200
    
class TestWAFGrok(unittest.TestCase):
    """Offline contract tests for the Nginx WAF Grok expression.

    These tests translate the small subset of Grok used by the WAF expression
    into Python regexes. They do NOT execute Logstash or verify New Relic output.
    Run the normal Logstash integration tests in Docker as well.
    """

    @classmethod
    def setUpClass(cls):
        cls.config = LOGSTASH_CONFIG.read_text(encoding='utf-8')
        match = re.search(
            r'^\s*"log_data"\s*=>\s*\'(\^NginxLog[^\n\']*)\'\s*$',
            cls.config,
            re.MULTILINE,
        )
        if not match:
            raise AssertionError('Expected Nginx WAF Grok rule in logstash.conf')

        grok_expression = match.group(1)
        grok_tokens = {
            'WORD': r'[A-Za-z0-9_]+',
            'INT': r'[+-]?[0-9]+',
            'NUMBER': r'[+-]?(?:[0-9]+(?:\.[0-9]+)?)',
        }

        def expand_grok_token(token):
            name, field = token.group(1), token.group(2)
            return '(?P<{}>{})'.format(field, grok_tokens[name])

        # Convert only the Grok tokens used by the Nginx WAF expression.
        python_expression = re.sub(
            r'%\{(WORD|INT|NUMBER):([a-z_]+)(?::int)?\}',
            expand_grok_token,
            grok_expression,
        )
        # Grok/Oniguruma uses (?<field>...), Python uses (?P<field>...).
        python_expression = re.sub(
            r'\(\?<([a-z_]+)>', r'(?P<\1>', python_expression
        )
        cls.pattern = re.compile(python_expression)

    def parse(self, line):
        match = self.pattern.fullmatch(line)
        self.assertIsNotNone(match, f'WAF Grok pattern did not match {line!r}')
        return match.groupdict()

    def test_waf_detection_extracts_request_attributes(self):
        fields = self.parse(
            'NginxLog "GET /dataset/123 HTTP/1.1" 429 456 "bot-detection"'
        )

        self.assertEqual(fields['http_method'], 'GET')
        self.assertEqual(fields['request'], '/dataset/123')
        self.assertEqual(fields['request_path'], '/dataset/123')
        self.assertEqual(fields['http_version'], '1.1')
        self.assertEqual(int(fields['nginx_status']), 429)
        self.assertEqual(int(fields['nginx_bytes_sent']), 456)
        self.assertEqual(fields['waf_detection'], 'bot-detection')

    def test_request_preserves_query_string_separately_from_path(self):
        fields = self.parse(
            'NginxLog "GET /dataset/123?keyword=water&page=2 HTTP/2.0" '
            '429 0 "rate-limit"'
        )

        self.assertEqual(fields['request'], '/dataset/123?keyword=water&page=2')
        self.assertEqual(fields['request_path'], '/dataset/123')
        self.assertEqual(fields['http_version'], '2.0')
        self.assertEqual(fields['waf_detection'], 'rate-limit')

    def test_query_parameter_permutations_are_preserved_verbatim(self):
        """Preserve order, repeated parameters, and punctuation for WAF analysis."""
        query_string = 'x=1&x=2&.**&.*&.**&x=3'
        fields = self.parse(
            f'NginxLog "GET /datasets?{query_string} HTTP/1.1" '
            '429 12 "query-permutation"'
        )

        self.assertEqual(fields['request'], f'/datasets?{query_string}')
        self.assertEqual(fields['request_path'], '/datasets')
        self.assertEqual(fields['waf_detection'], 'query-permutation')

    def test_percent_encoded_query_string_is_not_normalized(self):
        query_string = 'q=%2A%2A%26%2A&sort=asc%2Fdesc'
        fields = self.parse(
            f'NginxLog "GET /datasets?{query_string} HTTP/1.1" '
            '429 0 "bot-detection"'
        )

        self.assertEqual(fields['request'], f'/datasets?{query_string}')
        self.assertEqual(fields['request_path'], '/datasets')

    def test_post_request_and_multiple_detection_values(self):
        fields = self.parse(
            'NginxLog "POST /api/catalog HTTP/1.1" '
            '403 98 "bot:signal,rate-limit"'
        )

        self.assertEqual(fields['http_method'], 'POST')
        self.assertEqual(fields['request'], '/api/catalog')
        self.assertEqual(fields['request_path'], '/api/catalog')
        self.assertEqual(fields['waf_detection'], 'bot:signal,rate-limit')

    def test_missing_or_empty_detection_does_not_match(self):
        for line in (
            'NginxLog "GET /dataset HTTP/1.1" 200 321',
            'NginxLog "GET /dataset HTTP/1.1" 200 321 ""',
            'not an NginxLog event',
        ):
            with self.subTest(line=line):
                self.assertIsNone(self.pattern.fullmatch(line))

    def test_dash_detection_is_parsed_for_drop_filter(self):
        fields = self.parse(
            'NginxLog "GET /dataset HTTP/1.1" 200 321 "-"'
        )
        self.assertEqual(fields['waf_detection'], '-')

    def test_drop_condition_keeps_only_detected_nginx_events(self):
        # Check the real Logstash drop condition, not a Python reimplementation.
        self.assertRegex(
            self.config,
            r'\[log_data\]\s*=~\s*/\^NginxLog/\s+and\s+'
            r'\(!\[waf_detection\]\s+or\s+'
            r'\[waf_detection\]\s*==\s*"-"\)',
        )
        self.assertRegex(self.config, r'\[hostname\]\s*=~\s*/\^logstash-/')

    def test_existing_router_grok_is_preserved(self):
        # Router logs and WAF proxy logs remain separate events but both now
        # populate the `request` attribute with the complete request URI.
        self.assertIn('%{WORD:http_method} %{GREEDYDATA:request}', self.config)
        self.assertIn('x_forwarded_for:', self.config)

