"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""
from __future__ import annotations

import typing as t

from ..repository.aws_s3 import AwsS3RepositoryBackend
from .psql_dos import BasePsqlDosBackend
from .psql_s3 import PsqlS3StorageMigrator


class PsqlAwsS3StorageMigrator(PsqlS3StorageMigrator):
    """Subclass :class:`aiida.storage.psql_dos.migrator.PsqlDosMigrator` to customize the repository implementation."""

    def get_repository(self) -> AwsS3RepositoryBackend:
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        storage_config = self.profile.storage_config

        return AwsS3RepositoryBackend(
            aws_access_key_id=storage_config['aws_access_key_id'],
            aws_secret_access_key=storage_config['aws_secret_access_key'],
            region_name=storage_config['aws_region_name'],
            bucket_name=storage_config['aws_bucket_name'],
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
                'aws_bucket_name': {
                    'required': True,
                    'type': str,
                    'prompt': 'AWS bucket name',
                    'help': 'The name of the AWS S3 bucket to use.',
                },
            }
        )
        return options
