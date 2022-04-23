# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Test fixtures for the :mod:`aiida_s3` module."""
import boto3
from botocore.client import BaseClient
import moto
import pytest


@pytest.fixture(scope='session')
def aws_s3_config() -> dict:
    """Return a dictionary with mocked AWS S3 credentials."""
    return {
        'aws_access_key_id': 'mocked',
        'aws_secret_access_key': 'mocked',
        'region_name': 'mocked',
    }


@pytest.fixture(scope='session')
def aws_s3_client(aws_s3_config) -> BaseClient:
    """Mock an AWS S3 client for the session."""
    with moto.mock_s3():
        yield boto3.client('s3', **aws_s3_config)
