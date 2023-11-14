"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + S3."""
from __future__ import annotations

import typing as t

from aiida.storage.psql_dos.migrator import PsqlDosMigrator

from ..repository.s3 import S3RepositoryBackend
from .psql_dos import BasePsqlDosBackend


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


class PsqlS3Storage(BasePsqlDosBackend):
    """Storage backend using PostgresSQL and S3 object store."""

    migrator = PsqlS3StorageMigrator

    def get_repository(self) -> S3RepositoryBackend:  # type: ignore[override]
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
                'endpoint_url': {
                    'required': True,
                    'type': str,
                    'prompt': 'Server endpoint URL',
                    'help': 'The endpoint URL of the server to connect to.',
                },
                'access_key_id': {
                    'required': True,
                    'type': str,
                    'prompt': 'Access key ID',
                    'help': 'The access key ID.',
                },
                'secret_access_key': {
                    'required': True,
                    'type': str,
                    'prompt': 'Secret access key',
                    'help': 'The secret access key.',
                },
                'bucket_name': {
                    'required': True,
                    'type': str,
                    'prompt': 'Bucket name',
                    'help': 'The name of the S3 bucket to use.',
                },
            }
        )
        return options
