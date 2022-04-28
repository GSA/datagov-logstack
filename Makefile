logstash-installation:
	curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o logstash/awscliv2.zip
	curl https://artifacts.elastic.co/downloads/logstash/logstash-oss-7.16.3-linux-x86_64.tar.gz -o logstash/logstash-oss-7.16.3-linux-x86_64.tar.gz
	docker run -v $${PWD}:$${PWD} -w $${PWD} --rm docker.elastic.co/logstash/logstash-oss:7.16.3 bin/prepare-offline-logstash
