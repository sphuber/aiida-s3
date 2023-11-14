# pylint: disable=redefined-outer-name
"""Test fixtures for the :mod:`aiida_s3` module."""
from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import subprocess
import sys
import types
import typing as t
import uuid

import boto3
import botocore
import click
import moto
import pytest
from aiida.manage.configuration.profile import Profile

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']


def recursive_merge(left: dict[t.Any, t.Any], right: dict[t.Any, t.Any]) -> None:
    """Recursively merge the ``right`` dictionary into the ``left`` dictionary.

    :param left: Base dictionary.
    :param right: Dictionary to recurisvely merge on top of ``left`` dictionary.
    """
    for key, value in right.items():
        if key in left and isinstance(left[key], dict) and isinstance(value, dict):
            recursive_merge(left[key], value)
        else:
            left[key] = value


@dataclasses.dataclass
class CliResult:
    """Dataclass representing the result of a command line interface invocation."""

    stderr_bytes: bytes
    stdout_bytes: bytes
    exc_info: tuple[t.Type[BaseException], BaseException, types.TracebackType] | tuple[None, None, None] = (
        None,
        None,
        None,
    )
    exception: BaseException | None = None
    exit_code: int | None = 0

    @property
    def stdout(self) -> str:
        """Return the output that was written to stdout."""
        return self.stdout_bytes.decode('utf-8', 'replace').replace('\r\n', '\n')

    @property
    def stderr(self) -> str:
        """Return the output that was written to stderr."""
        return self.stderr_bytes.decode('utf-8', 'replace').replace('\r\n', '\n')

    @property
    def output_lines(self) -> list[str]:
        """Return the output that was written to stdout as a list of lines."""
        return self.stdout.split('\n')


@pytest.fixture
def run_cli_command():
    """Run a ``click`` command with the given options.

    The call will raise if the command triggered an exception or the exit code returned is non-zero.
    """
    from aiida_s3.cli import cmd_root

    def factory(
        arguments: list[str] | None = None,
        base_command: click.Command = cmd_root,
        raises: bool = False,
        use_subprocess: bool = True,
    ) -> CliResult:
        """Run the command and check the result.

        :param arguments: The command line arguments to pass to the invocation.
        :param base_command: The base command to invoke.
        :param raises: Boolean, if ``True``, the command should raise an exception.
        :param use_subprocess: Boolean, if ``True``, runs the command in a subprocess, otherwise it is run in the same
            interpreter using :class:`click.testing.CliRunner`. The advantage of running in a subprocess is that it
            simulates exactly what a user would invoke through the CLI. The test runner provided by ``click`` invokes
            commands in a way that is not always a 100% analogous to an actual CLI call and so tests may not cover the
            exact behavior. However, if a test monkeypatches the behavior of code that is called by the command being
            tested, then a subprocess cannot be used, since the monkeypatch only applies to the current interpreter. In
            these cases it is necessary to set ``use_subprocesses = False``.
        :returns: Instance of ``CliResult``.
        :raises AssertionError: If the command excepted and ``raises == True``, or if the command doesn't except and
            ``raises == False``.
        """
        from click.testing import CliRunner

        if use_subprocess:
            command = [base_command.name] if base_command.name else []
            command += arguments or []

            try:
                completed_process = subprocess.run(command, capture_output=True, check=True)
            except subprocess.CalledProcessError as exception:
                result = CliResult(
                    exc_info=sys.exc_info(),
                    exception=exception,
                    exit_code=exception.returncode,
                    stderr_bytes=exception.stderr,
                    stdout_bytes=exception.stdout,
                )
            else:
                result = CliResult(
                    stderr_bytes=completed_process.stderr,
                    stdout_bytes=completed_process.stdout,
                )
        else:
            result_click = CliRunner(mix_stderr=False).invoke(base_command, arguments or [])
            result = CliResult(
                exc_info=result_click.exc_info or (None, None, None),
                exception=result_click.exception,
                exit_code=result_click.exit_code,
                stderr_bytes=result_click.stderr_bytes or b'',
                stdout_bytes=result_click.stdout_bytes,
            )

        if raises:
            assert result.exception is not None, result.stdout
        else:
            assert result.exception is None, result.stderr

        return result

    return factory


@pytest.fixture(scope='session')
def should_mock_s3() -> bool:
    """Return whether the S3 client should be mocked this session or not.

    Returns the boolean equivalent of the ``AIIDA_S3_MOCK_S3`` environment variable. If it is not defined, ``True``
    is returned by default.

    :return: Boolean as to whether the S3 client connection should be mocked.
    """
    default = 'True'
    return os.getenv('AIIDA_S3_MOCK_S3', default) == default


@pytest.fixture(scope='session')
def s3_bucket_name(should_mock_s3) -> str:
    """Return the name of the bucket used for this session.

    Returns the value defined by the ``AIIDA_S3_BUCKET_NAME`` environment variable if defined and ``AIIDA_S3_MOCK_S3``
    is set to ``True``, otherwise generates a random name based on :func:`uuid.uuid4`.

    :return: Name of the bucket used for this session.
    """
    default = str(uuid.uuid4())
    return os.getenv('AIIDA_S3_BUCKET_NAME', default) if not should_mock_s3 else default


@pytest.fixture(scope='session')
def s3_config(should_mock_s3) -> dict:
    """Return a dictionary with S3 credentials.

    The credentials are taken from the ``AIIDA_S3_ENDPOINT_URL``, ``AIIDA_S3_ACCESS_KEY_ID`` and
    ``AIIDA_S3_SECRET_ACCESS_KEY`` environment variables, if and only if ``AIIDA_S3_MOCK_S3`` is set to ``True``,
    otherwise mocked values will be enforced.

    :return: Dictionary with parameters needed to initialize an S3 client. Contains the keys ``endpoint_url``,
    ``access_key_id`` and ``secret_access_key``.
    """
    return {
        'endpoint_url': os.getenv('AIIDA_S3_ENDPOINT_URL', 'localhost:9000') if not should_mock_s3 else None,
        'access_key_id': os.getenv('AIIDA_S3_ACCESS_KEY_ID') if not should_mock_s3 else 'mocked',
        'secret_access_key': os.getenv('AIIDA_S3_SECRET_ACCESS_KEY') if not should_mock_s3 else 'mocked',
    }


@pytest.fixture(scope='session', autouse=True)
def s3(should_mock_s3, s3_bucket_name, s3_config) -> t.Generator[dict, None, None]:
    """Return the S3 connection configuration for the session.

    The return value is a dictionary with the following keys:

        * `endpoint_url`
        * `access_key_id`
        * `secret_access_key`
        * `bucket_name`

    These values are provided by the ``s3_bucket_name`` and ``s3_config`` fixtures, respectively. See their
    documentation how to specify access credentials using environment variables.

    Unless ``AIIDA_S3_MOCK_S3`` is set to ``True``, the S3 client will be mocked for the entire session using
    the ``moto`` library.

    :return: Dictionary with the connection parameters used to connect to S3.
    """
    config = {
        'endpoint_url': s3_config['endpoint_url'],
        'access_key_id': s3_config['access_key_id'],
        'secret_access_key': s3_config['secret_access_key'],
        'bucket_name': s3_bucket_name,
    }
    context = moto.mock_s3 if should_mock_s3 else contextlib.nullcontext

    with context():
        yield config


@pytest.fixture(scope='session')
def s3_client(s3) -> botocore.client.BaseClient:
    """Return an S3 client for the session.

    A client using ``boto3`` will be initialised if and only if ``AIIDA_S3_MOCK_S3`` is set to ``True``. Otherwise
    the client will be mocked using ``moto``. The connection details will be provided by the dictionary returned by the
    ``s3`` session fixture.

    This client will use the bucket defined by the ``s3_bucket_name`` fixture and will clean it up at the end of the
    session. This means that when using this fixture, the cleanup is automatic. Note, however, that if other buckets are
    created, the tests bare the responsibility of cleaning those up themselves.
    """
    bucket_name = s3['bucket_name']
    client = boto3.client(
        's3',
        endpoint_url=s3['endpoint_url'],
        access_key_id=s3['access_key_id'],
        secret_access_key=s3['secret_access_key'],
    )

    try:
        yield client
    finally:
        try:
            client.head_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError:
            pass
        else:
            response = client.list_objects(Bucket=bucket_name)
            objects = response['Contents'] if 'Contents' in response else ()

            if objects:
                delete = {'Objects': [{'Key': obj['Key']} for obj in objects]}
                client.delete_objects(Bucket=bucket_name, Delete=delete)

            client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope='session')
def config_psql_s3(
    config_psql_dos: t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]],
    s3: dict[str, str],
) -> t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]]:
    """Return a profile configuration for the :class:`aiida_s3.storage.psql_s3.PsqlS3Storage`."""

    def factory(custom_configuration: dict[str, t.Any] | None = None) -> dict[str, t.Any]:
        """Return a profile configuration for the :class:`aiida_s3.storage.psql_s3.PsqlS3Storage`.

        :param custom_configuration: Custom configuration to override default profile configuration.
        :returns: The profile configuration.
        """
        configuration = config_psql_dos({})
        recursive_merge(configuration, {'storage': {'backend': 's3.psql_s3', 'config': {**s3}}})
        recursive_merge(configuration, custom_configuration or {})
        return configuration

    return factory


@pytest.fixture(scope='session')
def psql_s3_profile(aiida_profile_factory, config_psql_s3) -> t.Generator[Profile, None, None]:
    """Return a test profile configured for the :class:`aiida_s3.storage.psql_s3.PsqlS3Storage`."""
    yield aiida_profile_factory(config_psql_s3())


@pytest.fixture(scope='session')
def should_mock_aws_s3() -> bool:
    """Return whether the AWS S3 client should be mocked this session or not.

    Returns the boolean equivalent of the ``AIIDA_S3_MOCK_AWS_S3`` environment variable. If it is not defined, ``True``
    is returned by default.

    :return: Boolean as to whether the AWS S3 client connection should be mocked.
    """
    default = 'True'
    return os.getenv('AIIDA_S3_MOCK_AWS_S3', default) == default


@pytest.fixture(scope='session')
def aws_s3_bucket_name(should_mock_aws_s3) -> str:
    """Return the name of the bucket used for this session.

    Returns the value defined by the ``AIIDA_S3_AWS_BUCKET_NAME`` environment variable if defined and
    ``AIIDA_S3_MOCK_AWS_S3`` is set to ``True``, otherwise generates a random name based on :func:`uuid.uuid4`.

    :return: Name of the bucket used for this session.
    """
    default = str(uuid.uuid4())
    return os.getenv('AIIDA_S3_AWS_BUCKET_NAME', default) if not should_mock_aws_s3 else default


@pytest.fixture(scope='session')
def aws_s3_config(should_mock_aws_s3) -> dict:
    """Return a dictionary with AWS S3 credentials.

    The credentials are taken from the ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY`` and ``AWS_REGION_NAME``
    environment variables, if and only if ``AIIDA_S3_MOCK_AWS_S3`` is set to ``True``, otherwise mocked values will be
    enforced.

    :return: Dictionary with parameters needed to initialize an AWS S3 client. Contains the keys ``aws_access_key_id``,
        ``aws_secret_access_key`` and ``region_name``.
    """
    return {
        'aws_access_key_id': os.getenv('AIIDA_S3_AWS_ACCESS_KEY_ID') if not should_mock_aws_s3 else 'mocked',
        'aws_secret_access_key': os.getenv('AIIDA_S3_AWS_SECRET_ACCESS_KEY') if not should_mock_aws_s3 else 'mocked',
        'region_name': os.getenv('AIIDA_S3_AWS_REGION_NAME', 'eu-central-1') if not should_mock_aws_s3 else 'mocked',
    }


@pytest.fixture(scope='session', autouse=True)
def aws_s3(should_mock_aws_s3, aws_s3_bucket_name, aws_s3_config) -> t.Generator[dict, None, None]:
    """Return the AWS S3 connection configuration for the session.

    The return value is a dictionary with the following keys:

        * `aws_bucket_name`
        * `aws_access_key_id`
        * `aws_secret_access_key`
        * `aws_region_name`

    These values are provided by the ``aws_s3_bucket_name`` and ``aws_s3_config`` fixtures, respectively. See their
    documentation how to specify access credentials using environment variables.

    Unless ``AIIDA_S3_MOCK_AWS_S3`` is set to ``True``, the AWS S3 client will be mocked for the entire session using
    the ``moto`` library.

    :return: Dictionary with the connection parameters used to connect to AWS S3.
    """
    config = {
        'aws_bucket_name': aws_s3_bucket_name,
        'aws_access_key_id': aws_s3_config['aws_access_key_id'],
        'aws_secret_access_key': aws_s3_config['aws_secret_access_key'],
        'aws_region_name': aws_s3_config['region_name'],
    }
    context = moto.mock_s3 if should_mock_aws_s3 else contextlib.nullcontext

    with context():
        yield config


@pytest.fixture(scope='session')
def aws_s3_client(aws_s3) -> botocore.client.BaseClient:
    """Return an AWS S3 client for the session.

    A client using ``boto3`` will be initialised if and only if ``AIIDA_S3_MOCK_AWS_S3`` is set to ``True``. Otherwise
    the client will be mocked using ``moto``. The connection details will be provided by the dictionary returned by the
    ``aws_s3`` session fixture.

    This client will use the bucket defined by the ``aws_s3_bucket_name`` fixture and will clean it up at the end of the
    session. This means that when using this fixture, the cleanup is automatic. Note, however, that if other buckets are
    created, the tests bare the responsibility of cleaning those up themselves.
    """
    bucket_name = aws_s3['aws_bucket_name']
    client = boto3.client(
        's3',
        aws_access_key_id=aws_s3['aws_access_key_id'],
        aws_secret_access_key=aws_s3['aws_secret_access_key'],
        region_name=aws_s3['aws_region_name'],
    )

    try:
        yield client
    finally:
        try:
            client.head_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError:
            pass
        else:
            response = client.list_objects(Bucket=bucket_name)
            objects = response['Contents'] if 'Contents' in response else ()

            if objects:
                delete = {'Objects': [{'Key': obj['Key']} for obj in objects]}
                client.delete_objects(Bucket=bucket_name, Delete=delete)

            client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope='session')
def config_psql_aws_s3(
    config_psql_dos: t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]],
    aws_s3: dict[str, str],
) -> t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]]:
    """Return a profile configuration for the :class:`aiida_s3.storage.psql_aws_s3.PsqlAwsS3Storage`."""

    def factory(custom_configuration: dict[str, t.Any] | None = None) -> dict[str, t.Any]:
        """Return a profile configuration for the :class:`aiida_s3.storage.psql_aws_s3.PsqlAwsS3Storage`.

        :param custom_configuration: Custom configuration to override default profile configuration.
        :returns: The profile configuration.
        """
        configuration = config_psql_dos({})
        recursive_merge(configuration, {'storage': {'backend': 's3.psql_aws_s3', 'config': {**aws_s3}}})
        recursive_merge(configuration, custom_configuration or {})
        return configuration

    return factory


@pytest.fixture(scope='session')
def psql_aws_s3_profile(aiida_profile_factory, config_psql_aws_s3) -> t.Generator[Profile, None, None]:
    """Return a test profile configured for the :class:`aiida_s3.storage.psql_aws_s3.PsqlAwsS3Storage`."""
    yield aiida_profile_factory(config_psql_aws_s3())


@pytest.fixture(scope='session')
def should_mock_azure_blob() -> bool:
    """Return whether the Azure Blob Storage client should be mocked this session or not.

    Returns the boolean equivalent of the ``AIIDA_S3_MOCK_AZURE_BLOB`` environment variable. If it is not defined,
    ``True`` is returned by default.

    :return: Boolean as to whether the Azure Blob Storage client connection should be mocked.
    """
    default = 'True'
    return os.getenv('AIIDA_S3_MOCK_AZURE_BLOB', default) == default


@pytest.fixture(autouse=True)
def skip_if_azure_mocked(request, should_mock_azure_blob):
    """Skip if connection to Azure Blob storage should be mocked.

    Currently, it is not yet possible to successfully mock the Azure Blob storage, so the tests can only be run if
    proper credentials to the service are provided.
    """
    if request.node.get_closest_marker('skip_if_azure_mocked') and should_mock_azure_blob:
        pytest.skip('skipped because client is mocked')


@pytest.fixture(scope='session')
def azure_blob_container_name(should_mock_azure_blob) -> str:
    """Return the name of the container used for this session.

    Returns the value defined by the ``AIIDA_S3_AZURE_BLOB_CONTAINER_NAME`` environment variable if defined and
    ``AIIDA_S3_MOCK_AZURE_BLOB`` is set to ``True``, otherwise generates a random name based on :func:`uuid.uuid4`.

    :return: Name of the container used for this session.
    """
    default = str(uuid.uuid4())
    return os.getenv('AIIDA_S3_AZURE_BLOB_CONTAINER_NAME', default) if not should_mock_azure_blob else default


@pytest.fixture(scope='session')
def azure_blob_config(should_mock_azure_blob) -> dict:
    """Return a dictionary with Azure Blob Storage credentials.

    The credentials are taken from the ``AIIDA_S3_AZURE_BLOB_CONNECTION_STRING`` environment variable, if and only if
    ``AIIDA_S3_MOCK_AZURE_BLOB`` is set to ``True``, otherwise mocked values will be enforced.

    :return: Dictionary with parameters needed to initialize an Azure Blob Storage client. Contains the key
        ``connection_string``.
    """
    return {
        'connection_string': os.getenv('AIIDA_S3_AZURE_BLOB_CONNECTION_STRING')
        if not should_mock_azure_blob
        else 'mocked',
    }


@pytest.fixture(scope='session', autouse=True)
def azure_blob_storage(
    should_mock_azure_blob,
    azure_blob_container_name,
    azure_blob_config,
) -> t.Generator[dict[str, str], None, None]:
    """Return the Azure Blob Storage connection configuration for the session.

    The return value is a dictionary with the following keys:

        * `container_name`
        * `connection_string`

    These values are provided by the ``azure_blob_container_name`` and ``azure_blob_config`` fixtures, respectively. See
    their documentation how to specify access credentials using environment variables.

    Unless ``AIIDA_S3_MOCK_AZURE_BLOB`` is set to ``True``, the Azure Blob Service client will be mocked for the entire
    session using THE WHAT?.

    :return: Dictionary with the connection parameters used to connect to Azure Blob Storage service.
    """
    config = {
        'container_name': azure_blob_container_name,
        'connection_string': azure_blob_config['connection_string'],
    }
    context = contextlib.nullcontext if should_mock_azure_blob else contextlib.nullcontext

    with context():
        yield config


@pytest.fixture(scope='session')
def config_psql_azure_blob(
    config_psql_dos: t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]],
    azure_blob_storage: dict[str, str],
) -> t.Callable[[dict[str, t.Any] | None], dict[str, t.Any]]:
    """Return a profile configuration for the :class:`aiida_s3.storage.psql_azure_blob.PsqlAzureBlobStorage`."""

    def factory(custom_configuration: dict[str, t.Any] | None = None) -> dict[str, t.Any]:
        """Return a profile configuration for the :class:`aiida_s3.storage.psql_azure_blob.PsqlAzureBlobStorage`.

        :param custom_configuration: Custom configuration to override default profile configuration.
        :returns: The profile configuration.
        """
        configuration = config_psql_dos({})
        recursive_merge(configuration, {'storage': {'backend': 's3.psql_azure_blob', 'config': {**azure_blob_storage}}})
        recursive_merge(configuration, custom_configuration or {})
        return configuration

    return factory


@pytest.fixture(scope='session')
def psql_azure_blob_profile(
    should_mock_azure_blob,
    aiida_profile_factory,
    config_psql_azure_blob,
    azure_blob_storage,
) -> t.Generator[Profile, None, None] | None:
    """Return a test profile configured for the :class:`aiida_s3.storage.psql_azure_blob.PsqlAzureBlobStorage`."""
    from aiida_s3.repository.azure_blob import AzureBlobStorageRepositoryBackend

    if should_mock_azure_blob:
        # Azure cannot yet be successfully mocked, so if we are mocking, skip the test.
        yield None
        return

    try:
        yield aiida_profile_factory(config_psql_azure_blob())
    finally:
        repository = AzureBlobStorageRepositoryBackend(**azure_blob_storage)
        repository.erase()


@pytest.fixture
def generate_directory(tmp_path: pathlib.Path) -> t.Callable:
    """Construct a temporary directory with some arbitrary file hierarchy in it."""

    def _factory(metadata: dict | None = None) -> pathlib.Path:
        """Construct the contents of the temporary directory based on the metadata mapping.

        :param: file object hierarchy to construct. Each key corresponds to either a directory or file to create. If the
            value is a dictionary a directory is created with the name of the key. Otherwise it is assumed to be a file.
            The value should be the byte string that should be written to file or `None` if the file should be empty.
            Example metadata:

                {
                    'relative': {
                        'empty_folder': {},
                        'empty_file': None,
                        'filename': b'content',
                    }
                }

            will yield a directory with the following file hierarchy:

                relative
                ├── empty_folder
                │   └──
                ├── empty_file
                └── filename


        :return: the path to the temporary directory
        """
        if metadata is None:
            metadata = {}

        def create_files(basepath: pathlib.Path, data: dict):
            """Construct the files in data at the given basepath."""
            for key, values in data.items():
                filepath = basepath / key

                if isinstance(values, dict):
                    filepath.mkdir(parents=True, exist_ok=True)
                    create_files(filepath, values)
                else:
                    with open(filepath, 'wb') as handle:
                        if values is not None:
                            handle.write(values)

        create_files(tmp_path, metadata)

        return pathlib.Path(tmp_path)

    return _factory
