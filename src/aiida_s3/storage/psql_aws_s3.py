# -*- coding: utf-8 -*-
"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""
from aiida.storage.psql_dos import PsqlDosBackend

from ..repository.aws_s3 import AwsS3RepositoryBackend


class PsqlAwsS3Storage(PsqlDosBackend):
    """Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""

    def get_repository(self) -> AwsS3RepositoryBackend:  # type: ignore[override]
        """Return the backend to the file repository."""
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
