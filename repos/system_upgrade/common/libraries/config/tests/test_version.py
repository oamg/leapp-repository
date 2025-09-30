import pytest

from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import IPUSourceToPossibleTargets
from leapp.utils.deprecation import suppress_deprecation


def test_version_to_tuple():
    assert version._version_to_tuple('7.6') == (7, 6)


def test_validate_versions():
    version._validate_versions(['7.6', '7.7'])
    with pytest.raises(ValueError):
        assert version._validate_versions(['7.6', 'z.z'])


def test_comparison_operator_detection():
    assert not version._are_comparison_operators_used(['7.6', '7.7'])
    assert version._are_comparison_operators_used(['7.6', '< 7.7'])


def test_cmp_versions():
    assert version._cmp_versions(['>= 7.6', '< 7.7'])
    assert not version._cmp_versions(['>= 7.6', '& 7.7'])


def test_matches_version_wrong_args(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

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


def test_matches_version_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    assert not version.matches_version(['> 7.6', '< 7.7'], '7.6')
    assert not version.matches_version(['> 7.6', '< 7.7'], '7.7')
    assert not version.matches_version(['> 7.6', '< 7.10'], '7.6')
    assert not version.matches_version(['> 7.6', '< 7.10'], '7.10')
    assert not version.matches_version(['7.6', '7.7', '7.10'], '7.8')


def test_matches_version_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    assert version.matches_version(['7.6', '7.7', '7.10'], '7.7')
    assert version.matches_version(['> 7.6', '< 7.10'], '7.7')


def test_matches_version_centos_autocorrect(monkeypatch):
    actor_mock = CurrentActorMocked(release_id='centos',
                                    src_ver='8', dst_ver='9',
                                    virtual_source_version='8.10', virtual_target_version='9.5')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    assert version.matches_version(['8'], '8.10')
    assert version.matches_version(['9'], '9.5')
    assert not version.matches_version(['8'], '9.5')

    assert version.matches_version(['> 8', '<= 9'], '9.5')

    assert version.matches_version(['> 8.10', '<= 9.7'], '9')


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
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.6', dst_ver='8.1'))
    assert version.matches_target_version(*version_list) == result


@pytest.mark.parametrize('result,kernel,release_id,src_ver', [
    (True, '4.14.0-100.8.2.el7a.x86_64', 'rhel', '7.6'),
    (True, '4.14.0-100.8.2.el7a.x86_64', 'rhel', '7.9'),
    (False, '3.10.0-100.8.2.el7a.x86_64', 'rhel', '7.6'),
    (False, '4.14.0-100.8.2.el7a.x86_64', 'fedora', '7.6'),
    (False, '4.14.0-100.8.2.el7a.x86_64', 'fedora', '33'),
    (False, '5.14.0-100.8.2.el7a.x86_64', 'rhel', '7.6'),
    (False, '4.14.0-100.8.2.el8.x86_64', 'rhel', '8.1'),
    (False, '4.14.0-100.8.2.el9.x86_64', 'rhel', '9.1'),
])
@suppress_deprecation(version.is_rhel_alt)
def test_is_rhel_alt(monkeypatch, result, kernel, release_id, src_ver):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, kernel=kernel,
                                                                 release_id=release_id))
    assert version.is_rhel_alt() == result


@pytest.mark.parametrize('result,src_ver,is_saphana', [
    (True, '7.8', False),  # default rhel
    (False, '7.6', False),
    (True, '7.7', True),  # saphana
    (False, '7.6', True),
])
def test_is_supported_version(monkeypatch, result, src_ver, is_saphana):
    if is_saphana:
        supported_upgrade_paths = [IPUSourceToPossibleTargets(source_version='7.7', target_versions=['8.10'])]
    else:
        supported_upgrade_paths = [IPUSourceToPossibleTargets(source_version='7.8', target_versions=['8.10'])]

    actor_mock = CurrentActorMocked(src_ver=src_ver, supported_upgrade_paths=supported_upgrade_paths)
    monkeypatch.setattr(api, 'current_actor', actor_mock)
    assert version.is_supported_version() == result


@pytest.mark.parametrize('result,kernel,release_id', [
    (False, '3.10.0-790.el7.x86_64', 'rhel'),
    (False, '3.10.0-790.el7.x86_64', 'fedora'),
    (False, '3.10.0-790.35.2.rt666.1133.el7.x86_64', 'fedora'),
    (True, '3.10.0-790.35.2.rt666.1133.el7.x86_64', 'rhel'),
])
@suppress_deprecation(version.is_rhel_realtime)
def test_is_rhel_realtime(monkeypatch, result, kernel, release_id):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', kernel=kernel,
                                                                 release_id=release_id))
    assert version.is_rhel_realtime() == result


@pytest.mark.parametrize('result,sys_version', [
    ('7', '7.1.0'),
    ('7', '7.9'),
    ('7', '7'),
    ('8', '8.10'),
    ('10', '10.0'),
    ('10', '10.10.0'),
    ('10', '10.0'),
    ('10', '10'),
])
def test_get_major_version(result, sys_version):
    assert version.get_major_version(sys_version) == result
