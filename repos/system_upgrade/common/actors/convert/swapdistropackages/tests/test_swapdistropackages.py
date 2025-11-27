from unittest import mock

import pytest

from leapp.libraries.actor import swapdistropackages
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RpmTransactionTasks


def test_get_config(monkeypatch):
    test_config = {
        ("centos", "rhel"): {
            "swap": {"pkgA": "pkgB"},
            "remove": {
                "pkgC",
            },
        },
        ("centos", "rhel", 10): {"swap": {"pkg1": "pkg2"}},
    }
    monkeypatch.setattr(swapdistropackages, "_CONFIG", test_config)

    expect = {
        "swap": {"pkgA": "pkgB"},
        "remove": {
            "pkgC",
        },
    }
    # fallback to (centos, rhel) when there is no target version specific config
    cfg = swapdistropackages._get_config("centos", "rhel", 9)
    assert cfg == expect

    # has it's own target version specific config
    cfg = swapdistropackages._get_config("centos", "rhel", 10)
    assert cfg == {"swap": {"pkg1": "pkg2"}}

    # not mapped
    cfg = swapdistropackages._get_config("almalinux", "rhel", 9)
    assert not cfg


@pytest.mark.parametrize(
    "config,has_packages,expected",
    [
        (
            {
                "swap": {"pkgA": "pkgB"},
                "remove": {
                    "pkgC",
                },
            },
            ["pkgA", "pkgC"],
            RpmTransactionTasks(to_install=["pkgB"], to_remove=["pkgA", "pkgC"]),
        ),
        # only some pkgs present
        (
            {
                "swap": {"pkgA": "pkgB", "pkg1": "pkg2"},
                "remove": {"pkgC", "pkgD"},
            },
            ["pkg1", "pkgD"],
            RpmTransactionTasks(to_install=["pkg2"], to_remove=["pkg1", "pkgD"]),
        ),
        (
            {},
            [],
            RpmTransactionTasks(to_install=[], to_remove=[]),
        ),
    ],
)
def test__make_transaction_tasks(monkeypatch, config, has_packages, expected):
    monkeypatch.setattr(
        swapdistropackages, "has_package", lambda model, pkg: pkg in has_packages
    )

    tasks = swapdistropackages._make_transaction_tasks(config)
    assert tasks == expected


def test_process_ok(monkeypatch):
    curr_actor_mocked = CurrentActorMocked(src_distro='centos', dst_distro='rhel')
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)
    monkeypatch.setattr(swapdistropackages, "has_package", lambda model, pkg: True)

    swapdistropackages.process()

    expected = RpmTransactionTasks(
        to_install=[
            "redhat-logos",
            "redhat-logos-httpd",
            "redhat-logos-ipa",
            "redhat-indexhtml",
            "redhat-backgrounds",
            "redhat-release",
        ],
        to_remove=[
            "centos-logos",
            "centos-logos-httpd",
            "centos-logos-ipa",
            "centos-indexhtml",
            "centos-backgrounds",
            "centos-stream-release",
            "centos-gpg-keys",
            "centos-stream-repos",
            "centos-linux-release",
            "centos-linux-repos",
            "centos-obsolete-packages",
            "centos-release-automotive",
            "centos-release-automotive-experimental",
            "centos-release-autosd",
            "centos-release-ceph-pacific",
            "centos-release-ceph-quincy",
            "centos-release-ceph-reef",
            "centos-release-ceph-squid",
            "centos-release-ceph-tentacle",
            "centos-release-cloud",
            "centos-release-gluster10",
            "centos-release-gluster11",
            "centos-release-gluster9",
            "centos-release-hyperscale",
            "centos-release-hyperscale-experimental",
            "centos-release-hyperscale-experimental-testing",
            "centos-release-hyperscale-spin",
            "centos-release-hyperscale-spin-testing",
            "centos-release-hyperscale-testing",
            "centos-release-isa-override",
            "centos-release-kmods",
            "centos-release-kmods-kernel",
            "centos-release-kmods-kernel-6",
            "centos-release-messaging",
            "centos-release-nfs-ganesha4",
            "centos-release-nfs-ganesha5",
            "centos-release-nfs-ganesha6",
            "centos-release-nfs-ganesha7",
            "centos-release-nfs-ganesha8",
            "centos-release-nfv-common",
            "centos-release-nfv-openvswitch",
            "centos-release-okd-4",
            "centos-release-openstack-antelope",
            "centos-release-openstack-bobcat",
            "centos-release-openstack-caracal",
            "centos-release-openstack-dalmatian",
            "centos-release-openstack-epoxy",
            "centos-release-openstack-yoga",
            "centos-release-openstack-zed",
            "centos-release-openstackclient-xena",
            "centos-release-opstools",
            "centos-release-ovirt45",
            "centos-release-ovirt45-testing",
            "centos-release-proposed_updates",
            "centos-release-rabbitmq-38",
            "centos-release-samba414",
            "centos-release-samba415",
            "centos-release-samba416",
            "centos-release-samba417",
            "centos-release-samba418",
            "centos-release-samba419",
            "centos-release-samba420",
            "centos-release-samba421",
            "centos-release-samba422",
            "centos-release-samba423",
            "centos-release-storage-common",
            "centos-release-virt-common",
        ],
    )

    assert produce_mock.called == 1
    produced = produce_mock.model_instances[0]
    assert set(produced.to_install) == set(expected.to_install)
    assert set(produced.to_remove) == set(expected.to_remove)


def test_process_no_config_skip(monkeypatch):
    curr_actor_mocked = CurrentActorMocked(src_distro="distroA", dst_distro="distroB")
    monkeypatch.setattr(api, "current_actor", curr_actor_mocked)
    monkeypatch.setattr(swapdistropackages, "_get_config", lambda *args: None)
    monkeypatch.setattr(api, "current_logger", logger_mocked())
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, "produce", produce_mock)

    swapdistropackages.process()

    assert produce_mock.called == 0
    assert (
        "Could not find config for handling distro specific packages for distroA->distroB upgrade"
    ) in api.current_logger.warnmsg[0]


@pytest.mark.parametrize("distro", ["rhel", "centos"])
def test_process_not_converting_skip(monkeypatch, distro):
    curr_actor_mocked = CurrentActorMocked(src_distro=distro, dst_distro=distro)
    monkeypatch.setattr(api, "current_actor", curr_actor_mocked)
    monkeypatch.setattr(api, "current_logger", logger_mocked())
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, "produce", produce_mock)

    with mock.patch('leapp.libraries.actor.swapdistropackages._get_config') as _get_config_mocked:
        swapdistropackages.process()
        _get_config_mocked.assert_not_called()
        assert produce_mock.called == 0
