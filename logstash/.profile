#!/bin/bash

function parse_vcap_services () {
  if [[ -z "$VCAP_SERVICES" ]]; then
    return 0
  fi
  export DRAIN_USER=$(              echo "$VCAP_SERVICES" | jq -r '."user-provided"[0].credentials.DRAIN_USER')
  export DRAIN_PASSWORD=$(          echo "$VCAP_SERVICES" | jq -r '."user-provided"[0].credentials.DRAIN_PASSWORD')
  export AWS_ACCESS_KEY_ID=$(       echo "$VCAP_SERVICES" | jq -r ".s3[0].credentials.access_key_id")
  export AWS_SECRET_ACCESS_KEY=$(   echo "$VCAP_SERVICES" | jq -r ".s3[0].credentials.secret_access_key")
  export AWS_REGION=$(              echo "$VCAP_SERVICES" | jq -r ".s3[0].credentials.region")
  export AWS_BUCKET=$(              echo "$VCAP_SERVICES" | jq -r ".s3[0].credentials.bucket")
  export AWS_ENDPOINT="https://$(   echo "$VCAP_SERVICES" | jq -r ".s3[0].credentials.endpoint")"
  export AWS_S3_PROXY="$https_proxy"
}

parse_vcap_services

echo "Unpacking logstash..."
    tar xzvf logstash-oss-7.17.3-linux-x86_64.tar.gz > /dev/null 2>&1 && \
    rm logstash-oss-7.17.3-linux-x86_64.tar.gz
export LS_HOME="$PWD/logstash-7.17.3"

echo "Installing logstash plugins..."
"$LS_HOME"/bin/logstash-plugin install file://"$PWD"/plugins.zip

echo "Installing Cloud Foundry root CA certificate..."
cp "$LS_HOME"/jdk/lib/security/cacerts "$LS_HOME"/jdk/lib/security/jssecacerts
shopt -s nullglob # Skip the loop if there're no matching files
for cert in "${CF_SYSTEM_CERT_PATH:-/etc/cf-system-certificates}/*" ; do 
    echo "Installing certificates: $cert"
    # We haven't ever seen someone change this default password, and anyone who
    # can see this already has permission to update these files, so we're not
    # setting anything more complicated to avoid complications down the line.
    "$LS_HOME"/jdk/bin/keytool -noprompt -import -trustcacerts -file "$cert" -storepass changeit -alias "${cert/$CF_SYSTEM_CERT_PATH\//}" -keystore "$LS_HOME"/jdk/lib/security/jssecacerts
done

ln -s "$LS_HOME"/bin/logstash "$PWD"/bin/logstash || true
