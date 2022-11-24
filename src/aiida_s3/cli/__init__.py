# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Command line interface for ``aiida-s3``."""
from aiida.cmdline.groups.verdi import VerdiCommandGroup
import click


@click.group('aiida-s3', cls=VerdiCommandGroup)
def cmd_root():
    """Command line interface for ``aiida-s3``."""
