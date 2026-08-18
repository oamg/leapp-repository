import os

import leapp.libraries.common.config as ipu_config
from leapp.libraries.common.distro import distro_id_to_pretty_name, get_distro_iso_config
from leapp.libraries.common.mounting import LoopMount, MountError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import CustomTargetRepository, TargetOSInstallationImage


def etc_release_extract_version(etc_release_contents, target_distro):
    """
    Extract product release version from /etc/release content

    :return: The parsed version or None if it couldn't be determined
    :rtype: str | None
    """
    # 'Red Hat Enterprise Linux release 8.10 (Ootpa)' -> ['Red Hat Enterprise Linux', '8.10 (Ootpa)']
    # Red Hat Enterprise Linux release 9.8 (Plow)
    # CentOS Stream release 8
    api.current_logger().debug(
        'Determining OS version from etc release contents: {}'.format(etc_release_contents)
    )
    product_release_fragments = etc_release_contents.split('release')
    if len(product_release_fragments) != 2:
        api.current_logger().debug('Failed to determine OS version: Unexpected format of etc release')
        return None  # Unlikely. Either way we failed to parse the release

    required_distro = distro_id_to_pretty_name(target_distro)
    determined_distro = product_release_fragments[0].strip()
    if not determined_distro.startswith(required_distro):
        api.current_logger().debug(
            'Failed to determine OS version: The OS name from etc release ({}) does not match the'
            ' requested target distro ({})'.format(determined_distro, required_distro)
        )
        return None

    determined_ver = product_release_fragments[1].strip().split(' ', 1)[0]  # Remove release name (Maipo)
    return determined_ver


def determine_os_version_from_iso_mountpoint(iso_mountpoint):
    baseos_packages = os.path.join(iso_mountpoint, 'BaseOS/Packages')

    if not os.path.isdir(baseos_packages):
        return ''

    target_distro = ipu_config.get_target_distro_id()
    distro_iso_config = get_distro_iso_config(target_distro)

    def is_release_pkg(pkg_name):
        return (
            pkg_name.startswith(distro_iso_config.release_pkg_name_prefix)
            and 'eula' not in pkg_name
        )

    distro_release_pkgs = [pkg for pkg in os.listdir(baseos_packages) if is_release_pkg(pkg)]

    if not distro_release_pkgs:
        return ''  # We did not determine anything

    if len(distro_release_pkgs) > 1:
        api.current_logger().warning(
            'Multiple packages with name {}* found when determining target version of the supplied'
            ' installation ISO.'.format(distro_iso_config.release_pkg_name_prefix)
        )

    distro_release_pkg = distro_release_pkgs[0]

    try:
        release_pkg_path = os.path.join(baseos_packages, distro_release_pkg)
        # rpm2cpio is provided by rpm; cpio is a dependency of yum (rhel7) and a dependency of dracut which is
        # a dependency for leapp (rhel8+)
        cpio_archive = run(['rpm2cpio', release_pkg_path])
        etc_release_contents = run(
            [
                'cpio',
                '--extract',
                '--to-stdout',
                f'.{distro_iso_config.etc_release_file}',
            ],
            stdin=cpio_archive['stdout'],
        )

        return etc_release_extract_version(etc_release_contents['stdout'], target_distro) or ''
    except CalledProcessError:
        # FIXME?: This might fail e.g. if the ISO isn't complete
        # (download/scp/...) interrupted. Maybe we should at include
        # info that in the report?
        # Leaving an exact example from the logs (yes the empty line is there):
        # error:
        # /var/lib/leapp/iso_scan_mountpoint/BaseOS/Packages/centos-stream-release-9.0-26.el9.noarch.rpm:
        # read failed: Input/output error (5)

        # error reading header from package

        return ''


def inform_ipu_about_request_to_use_target_iso():
    target_iso_path = ipu_config.get_env('LEAPP_TARGET_ISO')
    if not target_iso_path:
        return

    iso_mountpoint = '/iso'

    if not os.path.exists(target_iso_path):
        # If the path does not exists, do not attempt to mount it and let the upgrade be inhibited by the check actor
        api.produce(TargetOSInstallationImage(path=target_iso_path,
                                              repositories=[],
                                              mountpoint=iso_mountpoint,
                                              was_mounted_successfully=False))
        return

    # Mount the given ISO, extract the available repositories and determine provided target version
    iso_scan_mountpoint = '/var/lib/leapp/iso_scan_mountpoint'
    try:
        with LoopMount(source=target_iso_path, target=iso_scan_mountpoint):
            required_repositories = ('BaseOS', 'AppStream')

            # Check what required repositories are present in the root of the ISO
            iso_contents = os.listdir(iso_scan_mountpoint)
            present_repositories = [req_repo for req_repo in required_repositories if req_repo in iso_contents]

            # Create custom repository information about the repositories found in the root of the ISO
            iso_repos = []
            for repo_dir in present_repositories:
                baseurl = 'file://' + os.path.join(iso_mountpoint, repo_dir)
                iso_repo = CustomTargetRepository(name=repo_dir, baseurl=baseurl, repoid=repo_dir)
                api.produce(iso_repo)
                iso_repos.append(iso_repo)

            os_version = determine_os_version_from_iso_mountpoint(iso_scan_mountpoint)

            api.produce(TargetOSInstallationImage(path=target_iso_path,
                                                  repositories=iso_repos,
                                                  mountpoint=iso_mountpoint,
                                                  rhel_version=os_version,
                                                  os_version=os_version,
                                                  was_mounted_successfully=True))
    except MountError:
        # Do not analyze the situation any further as ISO checks will be done by another actor
        iso_mountpoint = '/iso'
        api.produce(TargetOSInstallationImage(path=target_iso_path,
                                              repositories=[],
                                              mountpoint=iso_mountpoint,
                                              was_mounted_successfully=False))
