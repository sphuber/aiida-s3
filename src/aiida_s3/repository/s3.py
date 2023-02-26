# -*- coding: utf-8 -*-
"""Implementation of the :py:`aiida.repository.backend.abstract.AbstractRepositoryBackend` using S3 as backend."""
from __future__ import annotations

import contextlib
import tempfile
import typing as t
import uuid

from aiida.repository.backend.abstract import AbstractRepositoryBackend
import boto3
import botocore

__all__ = ('S3RepositoryBackend',)


class S3RepositoryBackend(AbstractRepositoryBackend):
    """Implementation of the ``AbstractRepositoryBackend`` using S3 as the backend."""

    def __init__(self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str):
        """Construct a new instance for a given bucket.

        .. note:: It is possible to construct an instance for a bucket that doesn't exist yet. To use the backend,
            however, the bucket needs to exist. To ensure it exists, call ``initialise``, which will create the bucket
            if it doesn't already.

        :param endpoint_url: The endpoint URL of the server to connect to.
        :param access_key_id: The access key ID to use to authenticate with S3.
        :param secret_access_key: The secret access key to use to authenticate with S3.
        :param bucket_name: The name of the bucket to use.
        """
        self._bucket_name = bucket_name
        self._client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def __str__(self) -> str:
        """Return the string representation of this repository."""
        return f'S3RepositoryBackend: <{self._bucket_name}>'

    @property
    def _bucket_exists(self) -> bool:
        """Return whether the bucket exists."""
        try:
            self._client.head_bucket(Bucket=self._bucket_name)
        except botocore.exceptions.ClientError:
            return False

        return True

    @property
    def is_initialised(self) -> bool:
        """Return whether the repository has been initialised.

        This amounts to whether the configured bucket actually exists. Calling ``initialise`` will create the bucket
        if it didn't already exist.
        """
        return self._bucket_exists

    def initialise(self, **kwargs) -> None:
        """Initialise the repository if it hasn't already been initialised.

        :param kwargs: parameters for the initialisation.
        """
        if self.is_initialised:
            return

        self._client.create_bucket(Bucket=self._bucket_name, **kwargs)

    @property
    def uuid(self) -> str:
        """Return the unique identifier of the repository."""
        return self._bucket_name

    @property
    def key_format(self) -> str | None:
        """Return the format for the keys of the repository."""
        return 'uuid4'

    def erase(self):
        """Delete the bucket configured for this instance and all its contents."""
        if not self._bucket_exists:
            return

        self.delete_objects(list(self.list_objects()))
        self._client.delete_bucket(Bucket=self._bucket_name)

    def _put_object_from_filelike(self, handle: t.BinaryIO) -> str:
        """Store the byte contents of a file in the repository.

        :param handle: filelike object with the byte content to be stored.
        :return: the generated fully qualified identifier for the object within the repository.
        :raises TypeError: if the handle is not a byte stream.
        """
        key = str(uuid.uuid4())
        self._client.put_object(Bucket=self._bucket_name, Body=handle, Key=key)
        return key

    def has_objects(self, keys: list[str]) -> list[bool]:
        """Return whether the repository has an object with the given key.

        :param keys: list of fully qualified identifiers for objects within the repository.
        :return: list of booleans, in the same order as the keys provided, with value True if the respective object
            exists and False otherwise.
        """
        existing_keys = set(self.list_objects())
        return [key in existing_keys for key in keys]

    @contextlib.contextmanager
    def open(self, key: str) -> t.Iterator[t.IO[bytes]]:  # type: ignore[override]
        """Open a file handle to an object stored under the given key.

        .. note:: this should only be used to open a handle to read an existing file. To write a new file use the method
            ``put_object_from_filelike`` instead.

        :param key: fully qualified identifier for the object within the repository.
        :return: yield a byte stream object.
        :raise FileNotFoundError: if the file does not exist.
        :raise OSError: if the file could not be opened.
        """
        super().open(key)
        with tempfile.TemporaryFile() as handle:
            self._client.download_fileobj(self._bucket_name, key, handle)
            handle.seek(0)
            yield handle

    def iter_object_streams(self, keys: list[str]) -> t.Iterator[tuple[str, t.IO[bytes]]]:  # type: ignore[override]
        """Return an iterator over the (read-only) byte streams of objects identified by key.

        .. note:: handles should only be read within the context of this iterator.

        :param keys: fully qualified identifiers for the objects within the repository.
        :return: an iterator over the object byte streams.
        :raise FileNotFoundError: if the file does not exist.
        :raise OSError: if a file could not be opened.
        """
        for key in keys:
            with self.open(key) as handle:
                yield key, handle

    def delete_objects(self, keys: list[str]) -> None:
        """Delete the objects from the repository.

        :param keys: list of fully qualified identifiers for the objects within the repository.
        :raise FileNotFoundError: if any of the files does not exist.
        :raise OSError: if any of the files could not be deleted.
        """
        super().delete_objects(keys)
        if keys:
            self._client.delete_objects(Bucket=self._bucket_name, Delete={'Objects': [{'Key': key} for key in keys]})

    def list_objects(self) -> t.Iterable[str]:
        """Return iterable that yields all available objects by key.

        :return: An iterable for all the available object keys.
        """
        response = self._client.list_objects(Bucket=self._bucket_name)

        if 'Contents' not in response:
            yield from ()
        else:
            for obj in self._client.list_objects(Bucket=self._bucket_name)['Contents']:
                yield obj['Key']

    def maintain(  # type: ignore[override]
        self,
        dry_run: bool = False,
        live: bool = True,
        pack_loose: bool = None,
        do_repack: bool = None,
        clean_storage: bool = None,
        do_vacuum: bool = None,
    ) -> dict:
        # pylint: disable=arguments-differ, unused-argument
        """Perform maintenance operations.

        :param live: if True, will only perform operations that are safe to do while the repository is in use.
        :param pack_loose: flag for forcing the packing of loose files.
        :param do_repack: flag for forcing the re-packing of already packed files.
        :param clean_storage: flag for forcing the cleaning of soft-deleted files from the repository.
        :param do_vacuum: flag for forcing the vacuuming of the internal database when cleaning the repository.
        :return: a dictionary with information on the operations performed.
        """
        return {}

    def get_info(  # type: ignore[override]
        self,
        detailed=False,
    ) -> dict[str, int | str | dict[str, int] | dict[str, float]]:
        # pylint: disable=arguments-differ, unused-argument
        """Return information on configuration and content of the repository."""
        return {}
