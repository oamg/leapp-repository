from collections import namedtuple

import pytest

from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api


class CurrentActorMocked(object):
    version = namedtuple('configuration', ['source', 'target'])('7.6', '8.0')
    configuration = namedtuple('configuration', ['version'])(version)


def test_version_to_tuple():
    assert version._version_to_tuple('7.6') == (7, 6)


def test_validate_versions():
    version._validate_versions(['7.6', '7.7'])
    with pytest.raises(ValueError):
        assert version._validate_versions(['7.6', 'z.z'])


def test_simple_versions():
    assert version._simple_versions(['7.6', '7.7'])
    assert not version._simple_versions(['7.6', '< 7.7'])


def test_cmp_versions():
    assert version._cmp_versions(['>= 7.6', '< 7.7'])
    assert not version._cmp_versions(['>= 7.6', '& 7.7'])


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
    assert not version.matches_version(['> 7.6', '< 7.7'], '7.6')
    assert not version.matches_version(['> 7.6', '< 7.7'], '7.7')
    assert not version.matches_version(['> 7.6', '< 7.10'], '7.6')
    assert not version.matches_version(['> 7.6', '< 7.10'], '7.10')
    assert not version.matches_version(['7.6', '7.7', '7.10'], '7.8')


def test_matches_version_pass():
    assert version.matches_version(['7.6', '7.7', '7.10'], '7.7')
    assert version.matches_version(['> 7.6', '< 7.10'], '7.7')


def test_matches_source_version_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert version.matches_source_version('7.6', '7.7')


def test_matches_source_version_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert not version.matches_source_version('7.5', '7.7')


def test_matches_target_version_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert version.matches_target_version('8.0', '8.1')


def test_matches_source_targetn_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert not version.matches_target_version('8.2')
