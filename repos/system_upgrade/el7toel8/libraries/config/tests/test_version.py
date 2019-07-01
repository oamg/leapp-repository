import pytest

from leapp.libraries.common.config import version


def test_version_to_tuple():
    assert version._version_to_tuple('7.6') == (7, 6)


def test_validate_versions():
    assert version._validate_versions(['7.6', '7.7']) is None
    with pytest.raises(ValueError):
        assert version._validate_versions(['7.6', 'z.z'])


def test_simple_versions():
    assert version._simple_versions(['7.6', '7.7']) is True
    assert version._simple_versions(['7.6', '< 7.7']) is False


def test_cmp_versions():
    assert version._cmp_versions(['>= 7.6', '< 7.7']) is True
    assert version._cmp_versions(['>= 7.6', '& 7.7']) is False


def test_matches_version_wrong_args():
    with pytest.raises(TypeError):
        version.matches_version('>= 7.6', '7.7')
    with pytest.raises(TypeError):
        version.matches_version([7.6, 7.7], '7.7')
    with pytest.raises(TypeError):
        version.matches_version(['7.6', '7.7'], 7.7)
    with pytest.raises(ValueError):
        version.matches_version(['>= 7.6', '> 7.7'], 'x.y')
    with pytest.raises(ValueError):
        version.matches_version(['>= 7.6', '7.7'], '7.7')
    with pytest.raises(ValueError):
        version.matches_version(['>= 7.6', '& 7.7'], '7.7')


def test_matches_version_fail():
    assert version.matches_version(['> 7.6', '< 7.7'], '7.6') is False
    assert version.matches_version(['> 7.6', '< 7.7'], '7.7') is False
    assert version.matches_version(['> 7.6', '< 7.10'], '7.6') is False
    assert version.matches_version(['> 7.6', '< 7.10'], '7.10') is False
    assert version.matches_version(['7.6', '7.7', '7.10'], '7.8') is False


def test_matches_version_pass():
    assert version.matches_version(['7.6', '7.7', '7.10'], '7.7') is True
    assert version.matches_version(['> 7.6', '< 7.10'], '7.7') is True
