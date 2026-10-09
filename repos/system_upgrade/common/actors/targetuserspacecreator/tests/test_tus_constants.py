import pytest

from leapp.libraries.actor import tus_constants

_SM_DISABLE_FLAGS = ['--disableplugin', 'subscription-manager']


@pytest.mark.parametrize(('target_version', 'expected_major'), [
    ('9.6', '9'),
    ('10.0', '10'),
    ('8.10', '8'),
])
def test_common_dnf_flags_without_skip_rhsm(target_version, expected_major):
    expected = [
        '--setopt=module_platform_id=platform:el{}'.format(expected_major),
        '--setopt=keepcache=1',
        '--releasever', target_version,
    ]

    assert tus_constants.common_dnf_flags(target_version, skip_rhsm=False) == expected


@pytest.mark.parametrize(('target_version', 'expected_major'), [
    ('9.6', '9'),
    ('10.0', '10'),
    ('8.10', '8'),
])
def test_common_dnf_flags_with_skip_rhsm_disables_sm_plugin(target_version, expected_major):
    expected = [
        '--setopt=module_platform_id=platform:el{}'.format(expected_major),
        '--setopt=keepcache=1',
        '--releasever', target_version,
    ] + _SM_DISABLE_FLAGS

    assert tus_constants.common_dnf_flags(target_version, skip_rhsm=True) == expected
