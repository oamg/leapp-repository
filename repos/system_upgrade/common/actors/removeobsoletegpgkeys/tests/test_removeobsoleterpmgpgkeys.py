import os
import unittest.mock as mock

import pytest

from leapp.libraries.actor import removeobsoleterpmgpgkeys
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RPM

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def common_folder_path_mocked(folder):
    return os.path.join(_CUR_DIR, "../../../files/", folder)


def test_is_key_installed(monkeypatch):
    installed_rpms = InstalledRPM(
        items=[
            RPM(
                name="gpg-pubkey",
                version="d4082792",
                release="5b32db75",
                epoch="0",
                packager="Red Hat, Inc. (auxiliary key 2) <security@redhat.com>",
                arch="noarch",
                pgpsig="",
            ),
            RPM(
                name="gpg-pubkey",
                version="2fa658e0",
                release="45700c69",
                epoch="0",
                packager="Red Hat, Inc. (auxiliary key) <security@redhat.com>",
                arch="noarch",
                pgpsig="",
            ),
            RPM(
                name="gpg-pubkey",
                version="12345678",
                release="abcdefgh",
                epoch="0",
                packager="made up",
                arch="noarch",
                pgpsig="",
            ),
        ]
    )

    monkeypatch.setattr(
        api, "current_actor", CurrentActorMocked(msgs=[installed_rpms])
    )

    assert removeobsoleterpmgpgkeys._is_key_installed("gpg-pubkey-d4082792-5b32db75")
    assert removeobsoleterpmgpgkeys._is_key_installed("gpg-pubkey-2fa658e0-45700c69")
    assert removeobsoleterpmgpgkeys._is_key_installed("gpg-pubkey-12345678-abcdefgh")
    assert not removeobsoleterpmgpgkeys._is_key_installed(
        "gpg-pubkey-db42a60e-37ea5438"
    )


@pytest.mark.parametrize(
    "version, expected",
    [
        ("9", ["gpg-pubkey-d4082792-5b32db75", "gpg-pubkey-2fa658e0-45700c69"]),
        ("8", ["gpg-pubkey-2fa658e0-45700c69"])
    ]
)
def test_get_obsolete_keys(monkeypatch, version, expected):
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(dst_ver=version))
    monkeypatch.setattr(api, "get_common_folder_path", common_folder_path_mocked)
    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_is_key_installed", lambda key: key in expected
    )

    keys = removeobsoleterpmgpgkeys._get_obsolete_keys()
    assert set(keys) == set(expected)


@pytest.mark.parametrize(
    "version, obsoleted_keys, expected",
    [
        ("10", None, []),
        ("10", {}, []),
        (
            "10",
            {"8": ["gpg-pubkey-888-abc"], "10": ["gpg-pubkey-10-10"]},
            ["gpg-pubkey-888-abc", "gpg-pubkey-10-10"],
        ),
        (
            "9",
            {"8": ["gpg-pubkey-888-abc"], "9": ["gpg-pubkey-999-def"]},
            ["gpg-pubkey-999-def", "gpg-pubkey-888-abc"],
        ),
        (
            "8",
            {"8": ["gpg-pubkey-888-abc"], "9": ["gpg-pubkey-999-def"]},
            ["gpg-pubkey-888-abc"],
        ),
    ],
)
def test_get_obsolete_keys_incomplete_data(
    monkeypatch, version, obsoleted_keys, expected
):
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(dst_ver=version))
    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_is_key_installed", lambda key: key in expected
    )

    def get_distribution_data_mocked(_distro):
        if obsoleted_keys is None:
            return {}
        return {"obsoleted-keys": obsoleted_keys}

    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "get_distribution_data", get_distribution_data_mocked
    )

    keys = removeobsoleterpmgpgkeys._get_obsolete_keys()
    assert set(keys) == set(expected)


@pytest.mark.parametrize(
    "distro, expected",
    [
        (
            "centos",
            [
                "gpg-pubkey-8483c65d-5ccc5b19",
                "gpg-pubkey-1d997668-621e3cac",
                "gpg-pubkey-1d997668-61bae63b",
            ],
        ),
        (
            "rhel",
            [
                "gpg-pubkey-fd431d51-4ae0493b",
                "gpg-pubkey-37017186-45761324",
                "gpg-pubkey-f21541eb-4a5233e8",
                "gpg-pubkey-897da07a-3c979a7f",
                "gpg-pubkey-2fa658e0-45700c69",
                "gpg-pubkey-d4082792-5b32db75",
                "gpg-pubkey-5a6340b3-6229229e",
                "gpg-pubkey-db42a60e-37ea5438",
            ],
        ),
    ],
)
def test_get_source_distro_keys(monkeypatch, distro, expected):
    """
    Test that the correct keys are returned for each distro.
    """
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(src_distro=distro))
    monkeypatch.setattr(api, "get_common_folder_path", common_folder_path_mocked)
    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_is_key_installed", lambda _key: True
    )

    keys = removeobsoleterpmgpgkeys._get_source_distro_keys()
    assert set(keys) == set(expected)


@pytest.mark.parametrize(
    "keys, should_register",
    [
        (["gpg-pubkey-d4082792-5b32db75"], True),
        ([], False)
    ]
)
def test_workaround_should_register(monkeypatch, keys, should_register):
    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_get_obsolete_keys", lambda: keys
    )
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked())

    removeobsoleterpmgpgkeys.process()
    assert api.produce.called == should_register


def test_process(monkeypatch):
    """
    Test that the correct path is taken depending on whether also converting
    """
    obsolete = ["gpg-pubkey-12345678-abcdefgh"]
    source_distro = ["gpg-pubkey-87654321-hgfedcba"]

    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_get_obsolete_keys", lambda: obsolete
    )
    monkeypatch.setattr(
        removeobsoleterpmgpgkeys, "_get_source_distro_keys", lambda: source_distro,
    )

    # upgrade only path
    monkeypatch.setattr(
        api, "current_actor", CurrentActorMocked(src_distro="rhel", dst_distro="rhel")
    )
    with mock.patch(
        "leapp.libraries.actor.removeobsoleterpmgpgkeys.register_dnfworkaround"
    ):
        removeobsoleterpmgpgkeys.process()
        removeobsoleterpmgpgkeys.register_dnfworkaround.assert_called_once_with(
            obsolete
        )

    # upgrade + conversion paths
    monkeypatch.setattr(
        api, "current_actor", CurrentActorMocked(src_distro="rhel", dst_distro="centos")
    )
    with mock.patch(
        "leapp.libraries.actor.removeobsoleterpmgpgkeys.register_dnfworkaround"
    ):
        removeobsoleterpmgpgkeys.process()
        removeobsoleterpmgpgkeys.register_dnfworkaround.assert_called_once_with(
            source_distro
        )

    monkeypatch.setattr(
        api, "current_actor", CurrentActorMocked(src_distro="centos", dst_distro="rhel")
    )
    with mock.patch(
        "leapp.libraries.actor.removeobsoleterpmgpgkeys.register_dnfworkaround"
    ):
        removeobsoleterpmgpgkeys.process()
        removeobsoleterpmgpgkeys.register_dnfworkaround.assert_called_once_with(
            source_distro
        )
