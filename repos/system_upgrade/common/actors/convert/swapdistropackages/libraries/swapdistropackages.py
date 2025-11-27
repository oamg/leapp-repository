from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RpmTransactionTasks

_CONFIG = {
    ("centos", "rhel"): {
        "swap": {
            "centos-logos": "redhat-logos",
            "centos-logos-httpd": "redhat-logos-httpd",
            "centos-logos-ipa": "redhat-logos-ipa",
            "centos-indexhtml": "redhat-indexhtml",
            "centos-backgrounds": "redhat-backgrounds",
            "centos-stream-release": "redhat-release",
        },
        "remove": {
            "centos-gpg-keys",
            "centos-stream-repos",
            # various release packages, typically contain repofiles
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
            # present on Centos (not Stream) 8, let's include them if they are potentially leftover
            "centos-linux-release",
            "centos-linux-repos",
            "centos-obsolete-packages",
        },
    },
}


def _get_config(source_distro, target_distro, target_major):
    key = (source_distro, target_distro, target_major)
    config = _CONFIG.get(key)
    if config:
        return config

    key = (source_distro, target_distro)
    return _CONFIG.get(key)


def _make_transaction_tasks(config):
    to_install = []
    to_remove = []
    for source_pkg, target_pkg in config.get("swap", {}).items():
        if has_package(DistributionSignedRPM, source_pkg):
            to_remove.append(source_pkg)
            to_install.append(target_pkg)

    for pkg in config.get("remove", {}):
        # this has_package call isn't strictly necessary as the actor
        # processing RpmTransactionTasks checks if the package is present, but
        # keeping it for consistency with the above
        if has_package(DistributionSignedRPM, pkg):
            to_remove.append(pkg)

    return RpmTransactionTasks(to_install=to_install, to_remove=to_remove)


def process():
    source_distro = get_source_distro_id()
    target_distro = get_target_distro_id()

    if source_distro == target_distro:
        return

    config = _get_config(source_distro, target_distro, get_target_major_version())
    if not config:
        api.current_logger().warning(
            "Could not find config for handling distro specific packages for {}->{} upgrade.".format(
                source_distro, target_distro
            )
        )
        return

    task = _make_transaction_tasks(config)
    api.produce(task)
