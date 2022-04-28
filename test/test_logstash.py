import time
import unittest

import requests


LOGSTASH_HEALTHCHECK = 'http://logstash:9600/?pretty'

class TestLogstash(unittest.TestCase):
  def test_anonymous_access_denied(self):
    response = requests.get('http://logstash:8080')
    assert response.status_code == 401

  def test_authorized_user_allowed(self):
    client = requests.Session()
    client.auth = ('logstash', 'logstash')

    response = client.get('http://logstash:8080')
    assert response.status_code == 200
