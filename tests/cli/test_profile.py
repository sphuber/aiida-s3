"""Tests for ``verdi profile setup``."""

import pathlib

import pytest
import yaml
from aiida.cmdline.commands.cmd_profile import profile_setup
from aiida.plugins import StorageFactory
from click.testing import CliRunner


def filepath_config():
    """Return an iterator over the files in the ``tests/static/config`` directory."""
    for filepath in (pathlib.Path(__file__).parent.parent / 'static' / 'config').iterdir():
        yield filepath


@pytest.mark.parametrize('filepath_config', filepath_config())
def test_setup(aiida_config_tmp, monkeypatch, filepath_config):
    """Test the ``verdi profile setup`` command for all storage backends.

    This will just verify that the command accepts the ``--config`` option with a valid YAML file containing the options
    for the command and that it creates a new profile. The command normally also initialises the storage backend but
    that usually requires credentials which are faked here and so the initialisation would fail. That is why the
    :meth:`aiida.orm.implementation.storage_backend.StorageBackend.initialise` method is monkeypatched to be a no-op.
    """
    from aiida.manage import configuration

    with filepath_config.open() as handle:
        profile_config = yaml.safe_load(handle)

    entry_point = f's3.{filepath_config.stem}'
    cls = StorageFactory(entry_point)
    profile_name = profile_config['profile']

    monkeypatch.setattr(cls, 'initialise', lambda *args: True)
    monkeypatch.setattr(configuration, 'create_default_user', lambda *args: None)

    result = CliRunner().invoke(profile_setup, [entry_point, '-n', '--config', str(filepath_config)])
    assert f'Success: Created new profile `{profile_name}`.' in result.output
    assert profile_name in aiida_config_tmp.profile_names
