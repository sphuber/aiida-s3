# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_s3.cli` module."""


def test_help(run_cli_command):
    """Test that command succeeds with the ``--help`` option."""
    assert 'Usage:' in run_cli_command(['aiida-s3', '--help']).stdout
