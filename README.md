# datagov-logstack

Run your own logging stack on cloud.gov using AWS Open Distro Elasticsearch.


## Setup

Set your application name.

    $ app_name=logstack

Copy `vars.example.yml` to `vars.yml` (or a space-specific version) and
customize for your application.

Create an Elasticsearch instance.

    $ cf create-service aws-elasticsearch es-medium ${app_name}-elasticsearch

Create a user provided service for [secrets](#secrets).

Push the applications.

    $ cf push --manifest manifest.yml --vars-file vars.yml


## Secrets

Generate some secrets for the logstack applications via a user provided service.

  $ cf cups ${app_name}-secrets -p KIBANA_USER,KIBANA_PASSWORD,LOGSTASH_USER,LOGSTASH_PASSWORD

Name | Description | Where to find?
---- | ----------- | --------------
KIBANA_PASSWORD | Password for basic authentication on the Kibana proxy | randomly generated
KIBANA_USER | Username for basic authentication on the Kibana proxy | randomly generated


## Logstash vs Fluentd

_Documenting some notes about running Fluentd vs Logstash as Cloud Foundry
applications, configured for parsing Cloud Foundry logs._

Fludentd (fluent-bit specifically) Pros:

- Smaller memory footprint
- Simple "out-of-the box" cf application


Logstash Pros:

- Lots of existing Cloud Foundry configuration exists


## Development

Build and publish logstash container.

    $ docker build logstash -t datagov/datagov-logstash:7.4.2
    $ docker push datagov/datagov-logstash:7.4.2


## Contributing

See [CONTRIBUTING](CONTRIBUTING.md) for additional information.


## Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
