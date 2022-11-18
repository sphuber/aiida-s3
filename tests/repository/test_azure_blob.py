# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Tests for the :mod:`aiida_s3.repository.azure_blob` module."""
import io
import typing as t
import uuid

import pytest

from aiida_s3.repository.azure_blob import AzureBlobStorageRepositoryBackend


@pytest.fixture(scope='function')
def repository_uninitialised(azure_blob_config) -> t.Generator[AzureBlobStorageRepositoryBackend, None, None]:
    """Return uninitialised instance of :class:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend`."""
    repository = AzureBlobStorageRepositoryBackend(str(uuid.uuid4()), **azure_blob_config)
    try:
        yield repository
    finally:
        repository.erase()


@pytest.fixture(scope='function')
def repository(azure_blob_config) -> t.Generator[AzureBlobStorageRepositoryBackend, None, None]:
    """Return initialised instance of :class:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend`."""
    repository = AzureBlobStorageRepositoryBackend(str(uuid.uuid4()), **azure_blob_config)
    repository.initialise()
    try:
        yield repository
    finally:
        repository.erase()


def test_initialise(repository_uninitialised):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.initialise` method."""
    repository = repository_uninitialised
    assert not repository.is_initialised

    # Initialise the repository, which means creating the bucket essentially.
    repository.initialise()
    assert repository.is_initialised

    # Make sure to cleanup by deleting the created bucket.
    repository.erase()


def test_uuid(repository):
    """Test the :prop:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.uuid` property."""
    assert repository.uuid == repository._container_name  # pylint: disable=protected-access


def test_key_format(repository):
    """Test the :prop:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.key_format` property."""
    assert repository.key_format == 'uuid4'


def test_erase(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.erase` method."""
    directory = generate_directory({'file_a': None})

    with open(directory / 'file_a', 'rb') as handle:
        key = repository.put_object_from_filelike(handle)

    assert repository.has_object(key)

    repository.erase()

    assert not repository.is_initialised


def test_erase_uninitialised(repository_uninitialised):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.erase` method for uninited repo.

    The method should not fail if the configure bucket does not exist.
    """
    assert repository_uninitialised.erase() is None


def test_put_object_from_filelike_raises(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.put_object_from_filelike`.

    Test invocations for which the method should raise an exception.
    """
    directory = generate_directory({'file_a': None})

    with pytest.raises(TypeError):
        repository.put_object_from_filelike(directory / 'file_a')  # Path-like object

    with pytest.raises(TypeError):
        repository.put_object_from_filelike(directory / 'file_a')  # String

    with pytest.raises(TypeError):
        with open(directory / 'file_a', encoding='utf8') as handle:
            repository.put_object_from_filelike(handle)  # Not in binary mode


def test_put_object_from_filelike(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.put_object_from_filelike` method."""
    directory = generate_directory({'file_a': None})

    with open(directory / 'file_a', 'rb') as handle:
        key = repository.put_object_from_filelike(handle)

    assert isinstance(key, str)


def test_has_objects(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.has_objects` method."""
    directory = generate_directory({'file_a': None})

    assert repository.has_objects(['non_existant']) == [False]

    with open(directory / 'file_a', 'rb') as handle:
        key = repository.put_object_from_filelike(handle)

    assert repository.has_objects([key]) == [True]


def test_open_raise(repository):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.open` method.

    Test invocations for which the method should raise an exception.
    """
    with pytest.raises(FileNotFoundError):
        with repository.open('non_existant'):
            pass


def test_open(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.open` method."""
    directory = generate_directory({'file_a': b'content_a', 'relative': {'file_b': b'content_b'}})

    with open(directory / 'file_a', 'rb') as handle:
        key_a = repository.put_object_from_filelike(handle)

    with open(directory / 'relative/file_b', 'rb') as handle:
        key_b = repository.put_object_from_filelike(handle)

    with repository.open(key_a) as handle:
        assert isinstance(handle, io.BufferedRandom)

    with repository.open(key_a) as handle:
        assert handle.read() == b'content_a'

    with repository.open(key_b) as handle:
        assert handle.read() == b'content_b'


def test_iter_object_streams(repository):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.iter_object_streams` method."""
    key = repository.put_object_from_filelike(io.BytesIO(b'content'))

    for _key, stream in repository.iter_object_streams([key]):
        assert _key == key
        assert stream.read() == b'content'


def test_delete_objects(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.delete_objects` method."""
    directory = generate_directory({'file_a': None})

    with open(directory / 'file_a', 'rb') as handle:
        key = repository.put_object_from_filelike(handle)

    assert repository.has_object(key)

    repository.delete_objects([key])
    assert not repository.has_object(key)

    # The call should not except when an empty list of keys is provided.
    assert repository.delete_objects([]) is None


def test_get_object_hash(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.get_object_hash` method."""
    directory = generate_directory({'file_a': b'content'})

    with open(directory / 'file_a', 'rb') as handle:
        key = repository.put_object_from_filelike(handle)

    assert repository.get_object_hash(key) == 'ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73'


def test_list_objects(repository, generate_directory):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.list_objects` method."""
    keys = []

    # First empty the repository because other tests may have added objects to it.
    repository.delete_objects(repository.list_objects())
    repository.initialise()

    directory = generate_directory({'file_a': b'content a', 'file_b': b'content b'})

    with open(directory / 'file_a', 'rb') as handle:
        keys.append(repository.put_object_from_filelike(handle))

    with open(directory / 'file_b', 'rb') as handle:
        keys.append(repository.put_object_from_filelike(handle))

    assert sorted(list(repository.list_objects())) == sorted(keys)


def test_get_info(repository):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.get_info` method."""
    assert repository.get_info() == {}


def test_maintain(repository):
    """Test :meth:`aiida_s3.repository.azure_blob.AzureBlobStorageRepositoryBackend.maintain` method."""
    assert repository.maintain() == {}
