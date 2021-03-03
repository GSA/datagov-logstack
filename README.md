# datagov-logdrain

Run your own Elasticsearch-Fluentd-Kibana stack on cloud.gov using AWS Open
Distro Elasticsearch.

## Setup

Set your application name.

    $ app_name=logdrain

Create an Elasticsearch instance.

    $ cf create-service aws-elasticsearch es-medium logdrain-elasticsearch

Push the application.

    $ cf push -f manifest.yml

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md) for additional information.


## Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
