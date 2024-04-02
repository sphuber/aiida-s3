"""Tests for the :mod:`aiida_s3.storage.psql_azure_blob` module."""

import io

import pytest
from aiida import orm
from aiida_s3.repository.azure_blob import AzureBlobStorageRepositoryBackend
from aiida_s3.storage.psql_azure_blob import PsqlAzureBlobStorage

pytestmark = pytest.mark.skip_if_azure_mocked


def test_get_repository(psql_azure_blob_profile):
    """Test the :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.get_repository` method."""
    storage = PsqlAzureBlobStorage(psql_azure_blob_profile)
    assert isinstance(storage.get_repository(), AzureBlobStorageRepositoryBackend)


@pytest.mark.usefixtures('psql_azure_blob_profile')
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
