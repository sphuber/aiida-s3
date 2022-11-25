# `aiida-s3`

AiiDA plugin that provides various storage backends that allow using cloud data storage services, such as AWS S3 and Azure Blob Storage.

Currently, the following storage backends are available:

* `s3.psql_aws_s3`: Database provided by PostgreSQL and file repository provided by [AWS S3](https://aws.amazon.com/s3/).
* `s3.psql_azure_blob`: Database provided by PostgreSQL and file repository provided by [Azure Blob Storage](https://azure.microsoft.com/en-us/products/storage/blobs/).


## Installation

The recommended method of installation is through the [`pip`](https://pip.pypa.io/en/stable/) package installer for Python:

    pip install aiida-s3

## Setup

To use one of the storage backends provided by `aiida-s3` with AiiDA, you need to create a profile for it:

1.  List the available storage backends:
    ```bash
    aiida-s3 profile setup --help
    ```

1.  Create a profile using one of the available storage backends by passing it as an argument to `aiida-s3 profile setup`, for example:
    ```bash
    aiida-s3 profile setup psql-aws-s3
    ```
    The command will prompt for the information required to setup the storage backend.
    After all information is entered, the storage backend is initialized, such as creating the database schema and creating file containers.
    If

1.  Create a default user for the profile:
    ```bash
    verdi -p profile-name user configure --set-default
    ```

1.  The profile is now ready to be used with AiiDA.
    Optionally, you can set it as the new default profile:
    ```bash
    verdi profile setdefault profile-name
    ```

1.  Optionally, to test that everything is working as intended, launch a test calculation:
    ```bash
    verdi devel launch-add
    ```

## Testing

The unit tests are implemented and run with [`pytest`](https://docs.pytest.org/).
To run them, install the package with the `tests` extra dependencies:

    pip install aiida-s3[tests]

The plugin provides interfaces to various services that require credentials, such as AWS S3 and Azure Blob Storage.
To run the test suite, one has to provide these credentials or the services have to be mocked.
Instructions for each service that is supported are provided below.

### AWS S3

The [AWS S3](https://aws.amazon.com/s3/) service is interfaced with through the [`boto3`](https://pypi.org/project/boto3/) Python SDK.
The [`moto`](https://pypi.org/project/moto/) library allows to mock this interface.
This makes it possible to run the test suite without any credentials.
To run the tests, simply execute `pytest`:

    pytest

By default, the interactions with AWS S3 are mocked through `moto` and no actual credentials are required.
To run the tests against an actual AWS S3 container, the credentials need to be specified through environment variables:

    export AIIDA_S3_MOCK_AWS_S3=False
    export AWS_BUCKET_NAME='some-bucket'
    export AWS_ACCESS_KEY_ID='access-key'
    export AWS_SECRET_ACCESS_KEY='secret-access-key'
    pytest


### Azure Blob Storage

The [Azure Blob Storage](https://azure.microsoft.com/en-us/products/storage/blobs/) is communicated with through the [`azure-blob-storage`](https://pypi.org/project/azure-storage-blob/) Python SDK.
Currently, there is no good way to mock the clients of this library.
Therefore, when the tests are run without credentials, and so the Azure Blob Storage client needs to be mocked, the tests are skipped.
To run the tests against an actual AWS S3 container, the credentials need to be specified through environment variables:

    export AIIDA_S3_MOCK_AZURE_BLOB=False
    export AZURE_BLOB_CONTAINER_NAME='some-container'
    export AZURE_BLOB_CONNECTION_STRING='DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net'
    pytest

The specified container does not have to exist yet, it will be created automatically.
The connection string can be obtained through the Azure portal.
