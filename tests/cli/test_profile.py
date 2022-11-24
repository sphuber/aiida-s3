# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Tests for the :mod:`aiida_s3.cli.cmd_profile` module."""
import pathlib

from aiida.plugins import StorageFactory
import pytest
import yaml


def filepath_config():
    """Return an iterator over the files in the ``tests/static/config`` directory."""
    for filepath in (pathlib.Path(__file__).parent.parent / 'static' / 'config').iterdir():
        yield filepath


@pytest.mark.parametrize('filepath_config', filepath_config())
def test_setup(aiida_instance, run_cli_command, monkeypatch, filepath_config):
    """Test the ``aiida-s3 profile setup`` command for all storage backends.

    This will just verify that the command accepts the ``--config`` option with a valid YAML file containing the options
    for the command and that it creates a new profile. The command normallyn also initialises the storage backend but
    that usually requires credentials which are faked here and so the initialisation would fail. That is why the
    :meth:`aiida.orm.implementation.storage_backend.StorageBackend.initialise` method is monkeypatched to be a no-op.
    """
    with filepath_config.open() as handle:
        profile_config = yaml.safe_load(handle)

    entry_point = f's3.{filepath_config.stem}'
    cls = StorageFactory(entry_point)
    profile_name = profile_config['profile_name']

    monkeypatch.setattr(cls, 'initialise', lambda *args: True)

    # Must set ``use_subprocess=False`` because the ``initialise`` method of the storage implementation needs to be
    # monkeypatched, because it will fail since the credentials for the services are fake.
    result = run_cli_command(['profile', 'setup', entry_point, '--config', str(filepath_config)], use_subprocess=False)
    assert f'Success: Created new profile `{profile_name}`.' in result.output_lines
    assert profile_name in aiida_instance.profile_names
