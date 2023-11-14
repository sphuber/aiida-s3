"""Implementation of :class:`aiida.orm.implementation.storage_backend.StorageBackend` using PostgreSQL + AWS S3."""
from __future__ import annotations

import collections
import typing as t

from aiida.storage.psql_dos import PsqlDosBackend

if t.TYPE_CHECKING:
    from aiida.plugins.entry_point import EntryPoint


class BasePsqlDosBackend(PsqlDosBackend):
    """Storage backend using PostgresSQL and AWS S3."""

    @classmethod
    def get_entry_point(cls) -> 'EntryPoint' | None:
        """Return the entry point with which this storage backend implementation is registered.

        :return: The entry point or ``None`` if not found.
        """
        from aiida.plugins.entry_point import get_entry_point_from_class

        return get_entry_point_from_class(cls.__module__, cls.__name__)[1]

    @classmethod
    def get_cli_options(cls) -> collections.OrderedDict:
        """Return the CLI options that would allow to create an instance of this class."""
        return collections.OrderedDict(cls._get_cli_options())

    @classmethod
    def _get_cli_options(cls) -> dict:
        """Return the CLI options that would allow to create an instance of this class."""
        return {
            'profile_name': {
                'required': True,
                'type': str,
                'prompt': 'Profile name',
                'help': 'The name of the profile.',
            },
            'postgresql_engine': {
                'required': True,
                'type': str,
                'prompt': 'Postgresql engine',
                'default': 'postgresql_psycopg2',
                'help': 'The engine to use to connect to the database.',
            },
            'postgresql_hostname': {
                'required': True,
                'type': str,
                'prompt': 'Postgresql hostname',
                'default': 'localhost',
                'help': 'The hostname of the PostgreSQL server.',
            },
            'postgresql_port': {
                'required': True,
                'type': int,
                'prompt': 'Postgresql port',
                'default': '5432',
                'help': 'The port of the PostgreSQL server.',
            },
            'postgresql_username': {
                'required': True,
                'type': str,
                'prompt': 'Postgresql username',
                'help': 'The username with which to connect to the PostgreSQL server.',
            },
            'postgresql_password': {
                'required': True,
                'type': str,
                'prompt': 'Postgresql password',
                'help': 'The password with which to connect to the PostgreSQL server.',
            },
            'postgresql_database_name': {
                'required': True,
                'type': str,
                'prompt': 'Postgresql database name',
                'help': 'The name of the database in the PostgreSQL server.',
            },
        }
