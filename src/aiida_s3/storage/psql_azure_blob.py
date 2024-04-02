"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + Azure."""

from __future__ import annotations

import typing as t

from aiida.storage.psql_dos.backend import PsqlDosBackend
from pydantic import Field

from ..repository.azure_blob import AzureBlobStorageRepositoryBackend
from .psql_s3 import PsqlS3StorageMigrator


class PsqlAzureBlobStorageMigrator(PsqlS3StorageMigrator):
    """Subclass :class:`aiida.storage.psql_dos.migrator.PsqlDosMigrator` to customize the repository implementation."""

    def reset_repository(self) -> None:
        """Reset the repository deleting the bucket and all its contents."""
        repository = self.get_repository()
        if repository.is_initialised:
            repository.delete_objects(repository.list_objects())

    def get_repository(self) -> AzureBlobStorageRepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        storage_config = self.profile.storage_config

        return AzureBlobStorageRepositoryBackend(
            container_name=storage_config['container_name'],
            connection_string=storage_config['connection_string'],
        )


class PsqlAzureBlobStorage(PsqlDosBackend):
    """Storage backend using PostgresSQL and Azure Blob Storage."""

    migrator = PsqlAzureBlobStorageMigrator

    class Model(PsqlDosBackend.Model):
        """Model describing required information to configure an instance of the storage."""

        container_name: str = Field(
            title='Container name',
            description='The Azure Blob Storage container name.',
        )
        connection_string: str = Field(
            title='Connection string',
            description='The Azure Blob Storage connection string.',
        )
        repository_uri: t.ClassVar[None]  # type: ignore[assignment,misc]

    def get_repository(self) -> AzureBlobStorageRepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()
