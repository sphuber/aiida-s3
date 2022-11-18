# -*- coding: utf-8 -*-
"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + Azure."""
from aiida.storage.psql_dos import PsqlDosBackend
from aiida.storage.psql_dos.migrator import PsqlDosMigrator

from ..repository.azure_blob import AzureBlobStorageRepositoryBackend


class PsqlAzureBlobStorageMigrator(PsqlDosMigrator):
    """Subclass :class:`aiida.storage.psql_dos.migrator.PsqlDosMigrator` to customize the repository implementation."""

    def get_repository_uuid(self) -> str:
        """Return the UUID of the repository.

        :returns: The UUID of the repository of the configured profile.
        """
        return self.get_repository().uuid

    def reset_repository(self) -> None:
        """Reset the repository deleting the bucket and all its contents."""
        repository = self.get_repository()
        if repository.is_initialised:
            repository.delete_objects(repository.list_objects())

    def initialise_repository(self) -> None:
        """Initialise the repository."""
        repository = self.get_repository()
        repository.initialise()

    @property
    def is_repository_initialised(self) -> bool:
        """Return whether the repository is initialised.

        :returns: Boolean, ``True`` if the repository is initalised, ``False`` otherwise.
        """
        return self.get_repository().is_initialised

    def get_repository(self) -> AzureBlobStorageRepositoryBackend:
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        storage_config = self.profile.storage_config
        container_name: str = storage_config['container_name']
        connection_string: str = storage_config['connection_string']

        return AzureBlobStorageRepositoryBackend(
            container_name=container_name,
            connection_string=connection_string,
        )


class PsqlAzureBlobStorage(PsqlDosBackend):
    """Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + Azure."""

    migrator = PsqlAzureBlobStorageMigrator

    def get_repository(self) -> AzureBlobStorageRepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()
