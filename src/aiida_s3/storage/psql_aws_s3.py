"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""

from __future__ import annotations

import typing as t

from aiida.storage.psql_dos import PsqlDosBackend
from pydantic import Field

from ..repository.aws_s3 import AwsS3RepositoryBackend
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


class PsqlAwsS3Storage(PsqlDosBackend):
    """Storage backend using PostgresSQL and AWS S3."""

    migrator = PsqlAwsS3StorageMigrator

    class Model(PsqlDosBackend.Model):
        """Model describing required information to configure an instance of the storage."""

        aws_access_key_id: str = Field(
            title='AWS access key ID',
            description='The AWS access key ID.',
        )
        aws_secret_access_key: str = Field(
            title='AWS secret access key',
            description='The AWS secret access key.',
        )
        aws_region_name: str = Field(
            title='AWS region',
            description='The AWS region name code, e.g., `eu-central-1`.',
        )
        aws_bucket_name: str = Field(
            title='AWS bucket name',
            description='The name of the AWS S3 bucket to use.',
        )
        repository_uri: t.ClassVar[None]  # type: ignore[assignment,misc]

    def get_repository(self) -> AwsS3RepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()
