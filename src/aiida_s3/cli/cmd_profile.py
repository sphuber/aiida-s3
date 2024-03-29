"""CLI commands to create profiles."""
import typing as t

import click
from aiida.cmdline.groups import DynamicEntryPointCommandGroup

from . import cmd_root

if t.TYPE_CHECKING:
    from aiida.orm.implementation.storage_backend import StorageBackend


@cmd_root.group('profile')  # type: ignore[has-type]
def cmd_profile():
    """Commands to create profiles."""


def create_profile(ctx: click.Context, cls: t.Type['StorageBackend'], non_interactive: bool, **kwargs):
    """Set up a new profile with an ``aiida-s3`` storage backend."""
    import contextlib
    import io

    from aiida.cmdline.utils import echo
    from aiida.common.exceptions import EntryPointError
    from aiida.manage.configuration import Profile, get_config
    from aiida.plugins.entry_point import get_entry_point_from_class

    _, storage_entry_point = get_entry_point_from_class(cls.__module__, cls.__name__)

    if storage_entry_point is None:
        raise EntryPointError(f'`{cls}` does not have a registered entry point.')

    profile_name = kwargs.pop('profile_name')
    profile_config = {
        'storage': {
            'backend': storage_entry_point.name,
            'config': {
                'database_engine': kwargs.pop('postgresql_engine'),
                'database_hostname': kwargs.pop('postgresql_hostname'),
                'database_port': kwargs.pop('postgresql_port'),
                'database_username': kwargs.pop('postgresql_username'),
                'database_password': kwargs.pop('postgresql_password'),
                'database_name': kwargs.pop('postgresql_database_name'),
            },
        },
        'process_control': {
            'backend': 'rabbitmq',
            'config': {
                'broker_protocol': 'amqp',
                'broker_username': 'guest',
                'broker_password': 'guest',
                'broker_host': '127.0.0.1',
                'broker_port': 5672,
                'broker_virtual_host': '',
            },
        },
    }

    profile_config['storage']['config'].update(**kwargs)  # type: ignore[attr-defined]
    profile = Profile(profile_name, profile_config)

    config = get_config()

    if profile.name in config.profile_names:
        echo.echo_critical(f'The profile `{profile.name}` already exists.')

    config.add_profile(profile)

    echo.echo_report('Initialising the storage backend.')
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            profile.storage_cls.initialise(profile)
    except Exception as exception:
        echo.echo_critical(
            f'Storage backend initialisation failed, probably because connection details are incorrect:\n{exception}'
        )
    else:
        echo.echo_success('Storage backend initialisation completed.')

    config.store()
    echo.echo_success(f'Created new profile `{profile.name}`.')


@cmd_profile.group(
    'setup',
    cls=DynamicEntryPointCommandGroup,
    command=create_profile,
    entry_point_group='aiida.storage',
    entry_point_name_filter=r's3\..*',
)
def cmd_profile_setup():
    """Set up a new profile with an ``aiida-s3`` storage backend."""
