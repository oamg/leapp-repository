import pytest

from leapp.libraries.actor import tus_constants


@pytest.mark.parametrize(
    ('target_version', 'skip_rhsm', 'expected'),
    [
        (
            '9.6',
            False,
            [
                '--setopt=module_platform_id=platform:el9',
                '--setopt=keepcache=1',
                '--releasever', '9.6',
            ],
        ),
        (
            '9.6',
            True,
            [
                '--setopt=module_platform_id=platform:el9',
                '--setopt=keepcache=1',
                '--releasever', '9.6',
                '--disableplugin', 'subscription-manager',
            ],
        ),
        (
            '10.0',
            False,
            [
                '--setopt=module_platform_id=platform:el10',
                '--setopt=keepcache=1',
                '--releasever', '10.0',
            ],
        ),
    ]
)
def test_common_dnf_flags(target_version, skip_rhsm, expected):
    assert tus_constants.common_dnf_flags(target_version, skip_rhsm) == expected
