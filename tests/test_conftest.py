# -*- coding: utf-8 -*-
"""Tests for the :mod:`tests.conftest` module."""
from botocore.client import BaseClient


def test_s3_client(aws_s3_client):
    """Test the ``aws_s3_client`` fixture."""
    assert isinstance(aws_s3_client, BaseClient)
