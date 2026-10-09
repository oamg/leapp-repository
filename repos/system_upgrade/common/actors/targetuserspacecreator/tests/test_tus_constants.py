import pytest

from leapp.libraries.actor import tus_constants


@pytest.mark.parametrize('target_version,expected_major', [
    ('9.6', '9'),
    ('10.0', '10'),
    ('8.10', '8'),
])
def test_common_dnf_flags_base(target_version, expected_major):
    flags = tus_constants.common_dnf_flags(target_version, skip_rhsm=False)

    assert '--setopt=module_platform_id=platform:el{}'.format(expected_major) in flags
    assert '--setopt=keepcache=1' in flags
    # releasever is passed as two consecutive tokens
    assert flags[flags.index('--releasever') + 1] == target_version
    # subscription-manager plugin is left enabled when RHSM is not skipped
    assert '--disableplugin' not in flags


def test_common_dnf_flags_skip_rhsm_disables_sm_plugin():
    flags = tus_constants.common_dnf_flags('9.6', skip_rhsm=True)

    assert flags[-2:] == ['--disableplugin', 'subscription-manager']
