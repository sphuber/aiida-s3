# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Test fixtures for the :mod:`aiida_s3` module."""
import contextlib
import io
import os
import pathlib
import typing as t
import uuid

import boto3
import botocore
import moto
import pytest


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

    Returns the value defined by the ``AWS_BUCKET_NAME`` environment variable if defined and ``AIIDA_S3_MOCK_AWS_S3`` is
    set to ``True``, otherwise generates a random name based on :func:`uuid.uuid4`.

    :return: Name of the bucket used for this session.
    """
    default = str(uuid.uuid4())
    return os.getenv('AWS_BUCKET_NAME', default) if not should_mock_aws_s3 else default


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
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID') if not should_mock_aws_s3 else 'mocked',
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY') if not should_mock_aws_s3 else 'mocked',
        'region_name': os.getenv('AWS_REGION_NAME', 'eu-central-1') if not should_mock_aws_s3 else 'mocked',
    }


@pytest.fixture(scope='session', autouse=True)
def aws_s3(should_mock_aws_s3, aws_s3_bucket_name, aws_s3_config) -> dict:
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
@contextlib.contextmanager
def postgres_cluster(database_name=None, database_username=None, database_password=None) -> dict:
    """Create a PostgreSQL cluster using ``pgtest`` and cleanup after the yield."""
    from aiida.manage.external.postgres import Postgres
    from pgtest.pgtest import PGTest

    postgres_config = {
        'database_engine': 'postgresql_psycopg2',
        'database_port': None,
        'database_hostname': None,
        'database_name': database_name or str(uuid.uuid4()),
        'database_username': database_username or 'guest',
        'database_password': database_password or 'guest',
    }

    try:
        cluster = PGTest()

        postgres = Postgres(interactive=False, quiet=True, dbinfo=cluster.dsn)
        postgres.create_dbuser(postgres_config['database_username'], postgres_config['database_password'], 'CREATEDB')
        postgres.create_db(postgres_config['database_username'], postgres_config['database_name'])

        postgres_config['database_hostname'] = postgres.host_for_psycopg2
        postgres_config['database_port'] = postgres.port_for_psycopg2

        yield postgres_config
    finally:
        cluster.close()


@pytest.fixture(scope='session')
def aiida_manager():
    """Return the global instance of the :class:`aiida.manage.manager.Manager`."""
    from aiida.manage import get_manager
    return get_manager()


@pytest.fixture(scope='session')
@contextlib.contextmanager
def aiida_cluster(tmp_path_factory, aiida_manager):
    """Create a temporary configuration instance.

    This creates a temporary directory with a clean `.aiida` folder and basic configuration file. The currently loaded
    configuration and profile are stored in memory and are automatically restored at the end of this context manager.

    :return: A new empty config instance.
    """
    from aiida.manage import configuration

    reset = False

    if configuration.CONFIG is not None:
        reset = True
        current_config = configuration.CONFIG
        current_config_path = current_config.dirpath
        current_profile_name = configuration.get_profile().name

    configuration.settings.AIIDA_CONFIG_FOLDER = tmp_path_factory.mktemp('config')
    configuration.settings.create_instance_directories()
    configuration.CONFIG = configuration.load_config(create=True)

    try:
        yield configuration.CONFIG
    finally:
        if reset:
            configuration.settings.AIIDA_CONFIG_FOLDER = current_config_path
            configuration.CONFIG = current_config
            aiida_manager.load_profile(current_profile_name, allow_switch=True)


@pytest.fixture(scope='session')
def aiida_profile(aiida_cluster, aiida_manager, aws_s3, postgres_cluster):
    """Docs."""
    from aiida.manage.configuration import Profile
    from aiida.orm import User

    with aiida_cluster as aiida_config, postgres_cluster as postgres_config:

        parameters = {
            'test_profile': True,
            'storage': {
                'backend': 's3.psql_aws_s3',
                'config': {
                    **postgres_config,
                    **aws_s3,
                    'repository_uri': f'file://{aiida_config.dirpath}',
                }
            },
            'process_control': {
                'backend': 'rabbitmq',
                'config': {
                    'broker_protocol': 'amqp',
                    'broker_username': 'guest',
                    'broker_password': 'guest',
                    'broker_host': '127.0.0.1',
                    'broker_port': 5672,
                    'broker_virtual_host': '',
                }
            }
        }

        with contextlib.redirect_stdout(io.StringIO()):
            profile_name = str(uuid.uuid4())
            profile = Profile(profile_name, parameters)
            profile.storage_cls.migrate(profile)

            aiida_config.add_profile(profile)
            aiida_config.set_default_profile(profile_name).store()

            aiida_manager.load_profile(profile_name, allow_switch=True)

            user = User(email='test@mail.com').store()
            profile.default_user_email = user.email

        yield profile


@pytest.fixture
def generate_directory(tmp_path: pathlib.Path) -> t.Callable:
    """Construct a temporary directory with some arbitrary file hierarchy in it."""

    def _factory(metadata: dict = None) -> pathlib.Path:
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
