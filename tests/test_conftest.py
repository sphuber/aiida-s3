"""Tests for the :mod:`tests.conftest` module."""
from botocore.client import BaseClient


def test_s3_client(aws_s3_client, aws_s3_config):
    """Test the ``aws_s3_client`` fixture."""
    assert isinstance(aws_s3_client, BaseClient)
    assert str(aws_s3_client._endpoint) == f's3(https://s3.{aws_s3_config["region_name"]}.amazonaws.com)'
