import pytest

from leapp.libraries.common.rpms import _parse_config_modification, get_leapp_dep_packages, get_leapp_packages
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


def test_parse_config_modification():
    # Empty means no modification
    data = []
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was modified
    data = [
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was just touched (timestamp does not match)
    data = [
        ".......T.  c /etc/ssh/sshd_config",
    ]
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was not modified (not listed at all)
    data = [
        ".......T.  c /etc/sysconfig/sshd",
    ]
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # Parse multiple lines
    data = [
        "S.5....T.  c /etc/sysconfig/sshd",
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert _parse_config_modification(data, "/etc/ssh/sshd_config")


@pytest.mark.parametrize(
    "major_version,component,result",
    [
        (
            None,
            None,
            [
                "leapp",
                "python3-leapp",
                "leapp-upgrade-el8toel9",
                "leapp-upgrade-el8toel9-fapolicyd",
                "snactor",
            ],
        ),
        ("7", None, ["leapp", "python2-leapp", "leapp-upgrade-el7toel8", "snactor"]),
        (
            "8",
            None,
            [
                "leapp",
                "python3-leapp",
                "leapp-upgrade-el8toel9",
                "leapp-upgrade-el8toel9-fapolicyd",
                "snactor",
            ],
        ),
        (
            ["7", "8"],
            None,
            [
                "leapp",
                "python2-leapp",
                "leapp-upgrade-el7toel8",
                "python3-leapp",
                "leapp-upgrade-el8toel9",
                "leapp-upgrade-el8toel9-fapolicyd",
                "snactor",
            ],
        ),
        (
            ["8", "9"],
            None,
            [
                "leapp",
                "python3-leapp",
                "leapp-upgrade-el8toel9",
                "leapp-upgrade-el8toel9-fapolicyd",
                "leapp-upgrade-el9toel10",
                "leapp-upgrade-el9toel10-fapolicyd",
                "snactor",
            ],
        ),
        ("8", "framework", ["leapp", "python3-leapp"]),
        (
            "9",
            "repository",
            ["leapp-upgrade-el9toel10", "leapp-upgrade-el9toel10-fapolicyd"],
        ),
    ],
)
def test_get_leapp_packages(major_version, component, result, monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='8.9', dst_ver='9.3'))

    kwargs = {}
    if major_version:
        kwargs["major_version"] = major_version
    if component:
        kwargs["component"] = component

    assert set(get_leapp_packages(** kwargs)) == set(result)


@pytest.mark.parametrize('major_version,component,result', [
   ('8', 'nosuchcomponent',
    (ValueError,
     r"component nosuchcomponent is unknown, available choices are \['cockpit', 'framework', 'repository', 'tools']")
    ),
   ('nosuchversion', "framework",
    (ValueError, r"major_version nosuchversion is unknown, available choices are \['7', '8', '9']")),
   ('nosuchversion', False,
    (ValueError, r"At least one component must be specified when calling this function,"
     r" available choices are \['cockpit', 'framework', 'repository', 'tools']")),
])
def test_get_leapp_packages_errors(major_version, component, result, monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='8.9', dst_ver='9.3'))

    kwargs = {}
    if major_version:
        kwargs["major_version"] = major_version
    if component is not None:
        kwargs["component"] = component

    exc_type, exc_msg = result
    with pytest.raises(exc_type, match=exc_msg):
        get_leapp_packages(**kwargs)


@pytest.mark.parametrize('major_version,component,result', [
    (None, None, ['leapp-deps', 'leapp-upgrade-el8toel9-deps']),
    ('8', 'framework', ['leapp-deps']),
    ("7", "tools", []),
])
def test_get_leapp_dep_packages(major_version, component, result, monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='8.9', dst_ver='9.3'))

    kwargs = {}
    if major_version:
        kwargs["major_version"] = major_version
    if component:
        kwargs["component"] = component

    assert frozenset(get_leapp_dep_packages(**kwargs)) == frozenset(result)
