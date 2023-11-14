"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + Azure."""
from __future__ import annotations

import typing as t

from ..repository.azure_blob import AzureBlobStorageRepositoryBackend
from .psql_dos import BasePsqlDosBackend
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


class PsqlAzureBlobStorage(BasePsqlDosBackend):
    """Storage backend using PostgresSQL and Azure Blob Storage."""

    migrator = PsqlAzureBlobStorageMigrator

    def get_repository(self) -> AzureBlobStorageRepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()

    @classmethod
    def _get_cli_options(cls) -> dict[str, t.Any]:
        """Return the CLI options that would allow to create an instance of this class."""
        options = super()._get_cli_options()
        options.update(
            **{
                'container_name': {
                    'required': True,
                    'type': str,
                    'prompt': 'Container name',
                    'help': 'The Azure Blob Storage container name.',
                },
                'connection_string': {
                    'required': True,
                    'type': str,
                    'prompt': 'Connection string',
                    'help': 'The Azure Blob Storage connection string.',
                },
            }
        )
        return options
