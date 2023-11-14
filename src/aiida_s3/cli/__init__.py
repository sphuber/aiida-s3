# pylint: disable=cyclic-import,wrong-import-position
"""Command line interface for ``aiida-s3``."""
import click
from aiida.cmdline.groups.verdi import VerdiCommandGroup


@click.group('aiida-s3', cls=VerdiCommandGroup)
def cmd_root():
    """Command line interface for ``aiida-s3``."""


from .cmd_profile import cmd_profile  # noqa
