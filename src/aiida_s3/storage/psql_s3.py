"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + S3."""

from __future__ import annotations

from aiida.storage.psql_dos.backend import PsqlDosBackend
from aiida.storage.psql_dos.migrator import PsqlDosMigrator
from pydantic import Field

from ..repository.s3 import S3RepositoryBackend


class PsqlS3StorageMigrator(PsqlDosMigrator):
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
            repository.erase()

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

    def get_repository(self) -> S3RepositoryBackend:
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        storage_config = self.profile.storage_config

        return S3RepositoryBackend(
            endpoint_url=storage_config['endpoint_url'],
            access_key_id=storage_config['access_key_id'],
            secret_access_key=storage_config['secret_access_key'],
            bucket_name=storage_config['bucket_name'],
        )


class PsqlS3Storage(PsqlDosBackend):
    """Storage backend using PostgresSQL and S3 object store."""

    migrator = PsqlS3StorageMigrator

    class Configuration(PsqlDosBackend.Configuration):
        """Model describing required information to configure an instance of the storage."""

        endpoint_url: str = Field(
            title='Server endpoint URL',
            description='The endpoint URL of the server to connect to.',
        )
        access_key_id: str = Field(
            title='Access key ID',
            description='The access key ID.',
        )
        secret_access_key: str = Field(
            title='Secret access key',
            description='The secret access key.',
        )
        bucket_name: str = Field(
            title='Bucket name',
            description='The name of the S3 bucket to use.',
        )

    def get_repository(self) -> S3RepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()
