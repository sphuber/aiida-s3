"""Tests for the :mod:`aiida_s3.storage.psql_aws_s3` module."""
import io

import pytest
from aiida import orm
from aiida_s3.repository.aws_s3 import AwsS3RepositoryBackend
from aiida_s3.storage.psql_aws_s3 import PsqlAwsS3Storage


def test_get_repository(psql_aws_s3_profile):
    """Test the :meth:`aiida_s3.repository.aws_s3.AwsS3RepositoryBackend.get_repository` method."""
    storage = PsqlAwsS3Storage(psql_aws_s3_profile)
    assert isinstance(storage.get_repository(), AwsS3RepositoryBackend)


@pytest.mark.usefixtures('psql_aws_s3_profile')
def test_node_storage():
    """Test storing and loading a node with attributes and file objects."""
    node = orm.Data()
    attributes = {'a': 1, 'b': 'string'}
    filename = 'file.txt'
    content = 'test content'

    node.base.attributes.set_many(attributes)
    node.base.repository.put_object_from_filelike(io.StringIO(content), filename)  # type: ignore[arg-type]
    node.store()

    loaded = orm.load_node(node.pk)
    assert loaded.base.attributes.all == attributes
    assert loaded.base.repository.get_object_content(filename) == content
