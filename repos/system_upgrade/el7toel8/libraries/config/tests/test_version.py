import pytest

from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


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


@pytest.mark.parametrize('result,version_list', [
    (True, ['7.6', '7.7']),
    (True, ['7.6']),
    (False, ['7.5', '7.7']),
    (False, ['7.5']),
])
def test_matches_source_version(monkeypatch, result, version_list):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.6'))
    assert version.matches_source_version(*version_list) == result


@pytest.mark.parametrize('result,version_list', [
    (True, ['8.0', '8.1']),
    (True, ['8.1']),
    (False, ['8.2']),
    (False, ['8.2', '8.0']),
])
def test_matches_target_version(monkeypatch, result, version_list):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.6'))
    assert version.matches_target_version(*version_list) == result


@pytest.mark.parametrize('result,kernel,release_id', [
    (True, '4.14.0-100.8.2.el7a.x86_64', 'rhel'),
    (False, '3.10.0-100.8.2.el7a.x86_64', 'rhel'),
    (False, '4.14.0-100.8.2.el7a.x86_64', 'fedora'),
    (False, '5.14.0-100.8.2.el7a.x86_64', 'rhel'),
])
def test_is_rhel_alt(monkeypatch, result, kernel, release_id):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.6', kernel=kernel,
                                                                 release_id=release_id))
    assert version.is_rhel_alt() == result


@pytest.mark.parametrize('result,is_alt,src_ver', [
    (True, True, '7.6'),
    (True, False, '7.8'),
    (False, True, '7.8'),
    (False, False, '7.6'),
])
def test_is_supported_version(monkeypatch, result, is_alt, src_ver):
    monkeypatch.setattr(version, 'is_rhel_alt', lambda: is_alt)
    monkeypatch.setattr(version, 'SUPPORTED_VERSIONS', {'rhel': ['7.8'], 'rhel-alt': ['7.6']})
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver))
    assert version.is_supported_version() == result
