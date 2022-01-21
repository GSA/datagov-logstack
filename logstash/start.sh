#!/bin/bash

set -o errexit
set -o pipefail

exec "bin/logstash -f logstash.conf"
