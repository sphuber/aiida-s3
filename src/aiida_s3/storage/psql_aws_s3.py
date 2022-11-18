# -*- coding: utf-8 -*-
"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""
from aiida.storage.psql_dos import PsqlDosBackend
from aiida.storage.psql_dos.migrator import PsqlDosMigrator

from ..repository.aws_s3 import AwsS3RepositoryBackend


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

        return AwsS3RepositoryBackend(
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )


class PsqlAwsS3Storage(PsqlDosBackend):
    """Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""

    migrator = PsqlAwsS3StorageMigrator

    def get_repository(self) -> AwsS3RepositoryBackend:  # type: ignore[override]
        """Return the file repository backend instance.

        :returns: The repository of the configured profile.
        """
        return self.migrator(self.profile).get_repository()
