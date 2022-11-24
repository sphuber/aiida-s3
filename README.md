# `aiida-s3`

AiiDA plugin that provides storage backend using AWS S3.


## Installation

The recommended method of installation is through the [`pip`](https://pip.pypa.io/en/stable/) package installer for Python:

    pip install aiida-s3

## Testing

The unit tests are implemented and run with [`pytest`](https://docs.pytest.org/).
To run them, install the package with the `tests` extra dependencies:

    pip install aiida-s3[tests]

The plugin provides interfaces to various services that require credentials, such as AWS S3 and Azure Blob Storage.
To run the test suite, one has to provide these credentials or the services have to be mocked.
Instructions for each service that is supported are provided below.

### AWS S3

The AWS S3 service is interfaced with through the [`boto3`](https://pypi.org/project/boto3/) Python SDK.
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
