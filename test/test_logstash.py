import time
import unittest

import requests


LOGSTASH_HEALTHCHECK = 'http://logstash:9600/?pretty'


class TestLogstash(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Wait for Logstash to be up
    while True:
      response = None
      try:
          response = requests.get(LOGSTASH_HEALTHCHECK)
      except:
          pass

      if response and response.status_code == 200:
        # Logstash is up, let's continue
        break
      time.sleep(1)


  def test_anonymous_access_denied(self):
    response = requests.get('http://logstash:5044')
    assert response.status_code == 401


  def test_authorized_user_allowed(self):
    client = requests.Session()
    client.auth = ('logstash', 'logstash')

    response = client.get('http://logstash:5044')
    assert response.status_code == 200
