# datagov-logstack

Run your own logging stack on cloud.gov using AWS Open Distro Elasticsearch.


## Usage

### Kibana

Use `cf env logstack-kibana` to get the basic authentication credentials.

Environment | URL
----------- | ---
management-staging | [logs-stage-datagov.app.cloud.gov](https://logs-stage-datagov.app.cloud.gov/_plugin/kibana/app/kibana)
management | [logs-datagov.app.cloud.gov](https://logs-datagov.app.cloud.gov/_plugin/kibana/app/kibana)


### Log drains

Use the [drain
plugin](https://github.com/cloudfoundry/cf-drain-cli#drain-all-apps-in-a-space)
to configure the log drain for all apps in a space. Alternatively, you can
configure the drain per-application following the [Cloud Foundry
documentation](https://docs.cloudfoundry.org/devguide/services/log-management.html).

Create a logdrain for you applications using the drains plugin within each
space. For the drain URL, this should match the HTTPS route you assigned to
Logstash (`logstash_routes`) and include the basic authentication credentials in
your user-provided service (see [secrets](#secrets)). _Note: creating
a space-wide drain may require org admin permissions in Cloud Foundry._

**Warning:** Do not add a space drain to the logstack-logstash's space or add the log
drain to itself. You'll amplify the logs and impact cloud.gov's loggregator.

    $ app_name=logstack
    $ space=production
    $ logstash_url=https://${logstash_user}:${logstash_password}@${logstash_route}
    $ cd $(mktemp -d)  # cd to a tempdir to avoid cf push picking up our manifest https://github.com/cloudfoundry/cf-drain-cli/issues/28
    $ cf drain-space --drain-name ${app_name}-space-drain-${space} ${logstash_url}

_Note: we include the space name in the drain name to work around
https://github.com/cloudfoundry/cf-drain-cli/issues/27._

After a short delay, logs should begin to flow automatically.


### Elasticsearch

- [Elasticsearch 7.4 docs](https://www.elastic.co/guide/en/elasticsearch/reference/7.4/index.html)


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
LOGSTASH_PASSWORD | Password for basic authentication on the Logstash proxy | randomly generated
LOGSTASH_USER | Username for basic authentication on the Logstash proxy | randomly generated


## Logstash vs Fluentd

_Documenting some notes about running Fluentd vs Logstash as Cloud Foundry
applications, configured for parsing Cloud Foundry logs._

Fludentd (fluent-bit specifically) Pros:

- Smaller memory footprint
- Simple "out-of-the box" cf application


Logstash Pros:

- Lots of existing Cloud Foundry configuration exists


## Applications

The logstack application is made up of several smaller Cloud Foundry
applications.

Name | Description
---- | -----------
logstack-kibana | Kibana proxy provides authentication to Kibana.
logstack-logstash | Logstash process that aggregates and parses log data.
logstack-space-drain | Space drain monitors the CF space, binds the log drain to applications. Created by the [drains plugin](https://github.com/cloudfoundry/cf-drain-cli).


## Development

Run tests.

    $ docker-compose run --rm test


## Contributing

See [CONTRIBUTING](CONTRIBUTING.md) for additional information.


## Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
