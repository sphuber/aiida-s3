# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Tests for the :mod:`aiida_s3.storage.psql_aws_s3` module."""
import io

from aiida import orm
import pytest

from aiida_s3.repository.aws_s3 import AwsS3RepositoryBackend
from aiida_s3.storage.psql_aws_s3 import PsqlAwsS3Storage


@pytest.fixture
def storage(aiida_profile):
    """Return an instance of :class:`aiida_s3.repository.aws_s3.PsqlAwsS3Storage` configured for the test profile."""
    return PsqlAwsS3Storage(profile=aiida_profile)


def test_get_repository(storage):
    """Test the :meth:`aiida_s3.repository.aws_s3.AwsS3RepositoryBackend.get_repository` method."""
    assert isinstance(storage.get_repository(), AwsS3RepositoryBackend)


def test_node_storage():
    """Test storing and loading a node with attributes and file objects."""
    node = orm.Data()
    attributes = {'a': 1, 'b': 'string'}
    filename = 'file.txt'
    content = 'test content'

    node.base.attributes.set_many(attributes)
    node.base.repository.put_object_from_filelike(io.StringIO(content), filename)
    node.store()

    loaded = orm.load_node(node.pk)
    assert loaded.base.attributes.all == attributes
    assert loaded.base.repository.get_object_content(filename) == content
