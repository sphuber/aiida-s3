"""Implementation of the :py:`aiida.repository.backend.abstract.AbstractRepositoryBackend` using Azure Blob Storage."""
from __future__ import annotations

import contextlib
import tempfile
import typing as t
import uuid

from aiida.repository.backend.abstract import AbstractRepositoryBackend
from azure.storage.blob import BlobServiceClient, ContainerClient

__all__ = ('AzureBlobStorageRepositoryBackend',)


class AzureBlobStorageRepositoryBackend(AbstractRepositoryBackend):
    """Implementation of the ``AbstractRepositoryBackend`` using Azure Blob Storage as the backend."""

    def __init__(self, container_name: str, connection_string: str):
        """Construct a new instance for a given storage account and container.

        .. note:: It is possible to construct an instance for a container that doesn't exist yet. To use the backend,
            however, the container needs to exist. To ensure it exists, call ``initialise``, which will create the
            container if it doesn't already.

        :param container_name: The name of the container to use.
        :param connection_string: The connection string for the Azure Blob Storage storage account.
        """
        self._container_name: str = container_name
        self._connection_string: str = connection_string

        try:
            self._service_client: BlobServiceClient = BlobServiceClient.from_connection_string(self._connection_string)
        except ValueError as exception:
            raise ValueError(
                f'could not connect with the given connection string: {self._connection_string}'
            ) from exception

        if self._service_client is None:
            raise ValueError(f'failed to connect with the given connection string: {self._connection_string}')

        self._container_client: ContainerClient = self._service_client.get_container_client(self._container_name)

    def __str__(self) -> str:
        """Return the string representation of this repository."""
        return f'AwsS3RepositoryBackend: <{self._container_name}>'

    @property
    def _container_exists(self) -> bool:
        """Return whether the container exists."""
        return self._container_client.exists()

    @property
    def is_initialised(self) -> bool:
        """Return whether the repository has been initialised.

        This amounts to whether the configured container actually exists. Calling ``initialise`` will create the
        container if it didn't already exist.
        """
        return self._container_exists

    def initialise(self, **kwargs: t.Any) -> None:
        """Initialise the repository if it hasn't already been initialised.

        :param kwargs: parameters for the initialisation.
        """
        if self.is_initialised:
            return

        self._container_client.create_container(**kwargs)

    @property
    def uuid(self) -> str:
        """Return the unique identifier of the repository."""
        return self._container_name

    @property
    def key_format(self) -> str:
        """Return the format for the keys of the repository."""
        return 'uuid4'

    def erase(self) -> None:
        """Delete the container configured for this instance and all its contents."""
        if not self._container_exists:
            return

        self._container_client.delete_container()

    def _put_object_from_filelike(self, handle: t.BinaryIO) -> str:
        """Store the byte contents of a file in the repository.

        :param handle: filelike object with the byte content to be stored.
        :return: the generated fully qualified identifier for the object within the repository.
        :raises TypeError: if the handle is not a byte stream.
        """
        key = str(uuid.uuid4())
        self._container_client.upload_blob(name=key, data=handle)
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
        with tempfile.TemporaryFile(mode='w+b') as handle:
            try:
                self._container_client.download_blob(key).readinto(handle)
            except Exception as exception:
                raise FileNotFoundError(f'object with key `{key}` does not exist.') from exception
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

    def delete_objects(self, keys: t.Iterable[str]) -> None:
        """Delete the objects from the repository.

        :param keys: list of fully qualified identifiers for the objects within the repository.
        :raise FileNotFoundError: if any of the files does not exist.
        :raise OSError: if any of the files could not be deleted.
        """
        super().delete_objects(list(keys))
        if keys:
            self._container_client.delete_blobs(*keys)

    def list_objects(self) -> t.Iterable[str]:
        """Return iterable that yields all available objects by key.

        :return: An iterable for all the available object keys.
        """
        for name in self._container_client.list_blob_names():
            yield name

    def maintain(  # type: ignore[override]  # noqa: PLR0913
        self,
        dry_run: bool = False,
        live: bool = True,
        pack_loose: bool | None = None,
        do_repack: bool | None = None,
        clean_storage: bool | None = None,
        do_vacuum: bool | None = None,
    ) -> dict[str, t.Any]:
        """Perform maintenance operations.

        :param live: if True, will only perform operations that are safe to do while the repository is in use.
        :param pack_loose: flag for forcing the packing of loose files.
        :param do_repack: flag for forcing the re-packing of already packed files.
        :param clean_storage: flag for forcing the cleaning of soft-deleted files from the repository.
        :param do_vacuum: flag for forcing the vacuuming of the internal database when cleaning the repository.
        :return: a dictionary with information on the operations performed.
        """
        return {}

    def get_info(self, detailed: bool = False, **kwargs: t.Any) -> dict[t.Any, t.Any]:
        """Return information on configuration and content of the repository."""
        return {}
