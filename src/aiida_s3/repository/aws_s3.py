"""Implementation of the :py:`aiida.repository.backend.abstract.AbstractRepositoryBackend` using AWS S3 as backend."""
from __future__ import annotations

import typing as t

import boto3

from .s3 import S3RepositoryBackend

__all__ = ('AwsS3RepositoryBackend',)


class AwsS3RepositoryBackend(S3RepositoryBackend):
    """Implementation of the ``AbstractRepositoryBackend`` using S3 as the backend."""

    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str, bucket_name: str):
        """Construct a new instance for a given bucket.

        .. note:: It is possible to construct an instance for a bucket that doesn't exist yet. To use the backend,
            however, the bucket needs to exist. To ensure it exists, call ``initialise``, which will create the bucket
            if it doesn't already.

        :param aws_access_key_id: The AWS access key ID to use to authenticate with AWS S3.
        :param aws_secret_access_key: The AWS secret access key to use to authenticate with AWS S3.
        :param region_name: The AWS region name to create the bucket in if it doesn't yet exist.
        :param bucket_name: The name of the bucket to use.
        """
        self._bucket_name = bucket_name
        self._region_name = region_name
        self._client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def __str__(self) -> str:
        """Return the string representation of this repository."""
        return f'AwsS3RepositoryBackend: <{self._bucket_name}>'

    def initialise(self, **kwargs: t.Any) -> None:
        """Initialise the repository if it hasn't already been initialised.

        :param kwargs: parameters for the initialisation.
        """
        if self._region_name is not None:
            kwargs['CreateBucketConfiguration'] = {'LocationConstraint': self._region_name}

        super().initialise(**kwargs)
