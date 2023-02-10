# -*- coding: utf-8 -*-
"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""
from __future__ import annotations

import typing as t

from aiida.storage.psql_dos.migrator import PsqlDosMigrator

from ..repository.aws_s3 import AwsS3RepositoryBackend
from .psql_dos import BasePsqlDosBackend


class PsqlAwsS3StorageMigrator(PsqlDosMigrator):
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

    def get_repository(self) -> AwsS3RepositoryBackend:
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        storage_config = self.profile.storage_config
        bucket_name: str = storage_config['aws_bucket_name']
        aws_access_key_id: str = storage_config['aws_access_key_id']
        aws_secret_access_key: str = storage_config['aws_secret_access_key']
        region_name: str = storage_config['aws_region_name']
        endpoint_url: str | None = storage_config['endpoint_url'] if 'endpoint_url' in storage_config else None

        return AwsS3RepositoryBackend(
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
        )


class PsqlAwsS3Storage(BasePsqlDosBackend):
    """Storage backend using PostgresSQL and AWS S3."""

    migrator = PsqlAwsS3StorageMigrator

    def get_repository(self) -> AwsS3RepositoryBackend:  # type: ignore[override]
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
                'aws_bucket_name': {
                    'required': True,
                    'type': str,
                    'prompt': 'AWS bucket name',
                    'help': 'The name of the AWS S3 bucket to use.',
                },
                'aws_access_key_id': {
                    'required': True,
                    'type': str,
                    'prompt': 'AWS access key ID',
                    'help': 'The AWS access key ID.',
                },
                'aws_secret_access_key': {
                    'required': True,
                    'type': str,
                    'prompt': 'AWS secret access key',
                    'help': 'The AWS secret access key.',
                },
                'aws_region_name': {
                    'required': True,
                    'type': str,
                    'prompt': 'AWS region',
                    'help': 'The AWS region name code, e.g., `eu-central-1`.',
                },
                'endpoint_url': {
                    'required': False,
                    'type': str,
                    'prompt': 'S3 API endpoint',
                    'help': 'Endpoint for supporting alternative S3 API providers'
                }
            }
        )
        return options
