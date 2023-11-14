"""Tests for the :mod:`aiida_s3` module."""
import aiida_s3
from packaging.version import Version, parse


def test_version():
    """Test that :attr:`aiida_s3.__version__` is a PEP-440 compatible version identifier."""
    assert hasattr(aiida_s3, '__version__')
    assert isinstance(aiida_s3.__version__, str)
    assert isinstance(parse(aiida_s3.__version__), Version)
