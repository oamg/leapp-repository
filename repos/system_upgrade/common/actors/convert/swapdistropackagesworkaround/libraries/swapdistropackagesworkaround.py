import itertools
import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting, rhsm
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version, get_target_version
from leapp.libraries.common.gpg import is_nogpgcheck_set
from leapp.libraries.stdlib import api, CalledProcessError, config
from leapp.models import DistributionSignedRPM, DNFWorkaround, TargetUserSpaceInfo, UsedTargetRepositories

SWAP_DATA_DIR = '/var/lib/leapp/swap-workaround-data'
DNF_SHELL_INSTRUCTIONS_PATH = os.path.join(SWAP_DATA_DIR, 'dnfshellinstructions')
_CONTAINER_DATA_DIR = '/swap-workaround-data'

# Oracle's redhat-release has a higher epoch than RHEL's, so dnf treats it as
# newer and considers the RHEL redhat-release already satisfied - it won't be
# installed. Removing Oracle's redhat-release lets the RHEL one in. For el8 -> el9
# this is done here, early, because the el9 redhat-release installs against the
# el8 rpm. For el9 -> el10 it can't be (the el10 redhat-release requires a newer
# rpm than el9 provides, and rpm is only upgraded once the repos are enabled), so
# swap_distro_packages removes it during the main upgrade instead. process() only
# adds this entry for el8 -> el9.
_OL_REDHAT_RELEASE_SWAP = {"install": ["redhat-release"], "remove": ["oraclelinux-release", "redhat-release"]}

_CONFIG = {
    # Oracle's logos/indexhtml/backgrounds packages obsolete their RHEL
    # counterparts, which would otherwise keep the RHEL versions from installing.
    # Remove the Oracle ones and install the RHEL ones together here, so the RHEL
    # versions are in place before the main upgrade and still provide what other
    # packages need (e.g. system-logos).
    ("ol", "rhel"): [
        {"install": ["redhat-logos"], "remove": ["oracle-logos", "plymouth-theme-spinner"]},
        {"install": ["redhat-indexhtml"], "remove": ["oracle-indexhtml"]},
        {"install": ["redhat-backgrounds"], "remove": ["oracle-backgrounds"]},
    ],
}


def _select_swaps(swap_config, installed_pkgs):
    """
    Pick the swap entries that apply to the current system.

    An entry applies when any of the packages it removes is actually installed.
    """
    return [
        entry for entry in swap_config
        if any(pkg in installed_pkgs for pkg in entry["remove"])
    ]


def _get_target_repoids(used_repos):
    repoids = set()
    for message in used_repos:
        repoids.update(repo.repoid for repo in message.repos)
    return sorted(repoids)


def _prepare_data_dir():
    """
    Create a clean data directory for the downloaded RPMs and instructions.
    """
    if os.path.isdir(SWAP_DATA_DIR):
        shutil.rmtree(SWAP_DATA_DIR)
    os.makedirs(SWAP_DATA_DIR)


def _download_packages(packages, target_userspace_info, used_repos):
    """
    Download the given target packages into SWAP_DATA_DIR.

    The download runs inside the target userspace container (which has the target
    repositories configured) with only the target repositories enabled, so the
    resolved packages are the target-distro builds. SWAP_DATA_DIR is bind-mounted
    into the container so `dnf download` writes the RPMs directly to their final
    location on the source system.
    """
    target_repoids = _get_target_repoids(used_repos)
    if not target_repoids:
        raise StopActorExecutionError(
            "Cannot download packages for the distribution swap workaround: "
            "no target repositories are available."
        )

    binds = ['{}:{}'.format(SWAP_DATA_DIR, _CONTAINER_DATA_DIR)]
    repos_opt = list(itertools.chain(*[['--enablerepo', repo] for repo in target_repoids]))
    cmd = [
        'dnf',
        'download',
        '--setopt=module_platform_id=platform:el{}'.format(get_target_major_version()),
        '--releasever', get_target_version(),
        '--disablerepo', '*',
    ] + repos_opt + [
        '--destdir', _CONTAINER_DATA_DIR,
    ] + list(packages)
    if is_nogpgcheck_set():
        cmd.append('--nogpgcheck')
    if config.is_verbose():
        cmd.append('-v')
    if rhsm.skip_rhsm():
        cmd += ['--disableplugin', 'subscription-manager']

    env = {}
    if get_target_major_version() == '9':
        # allow handling new RHEL 9 syscalls by systemd-nspawn
        env = {'SYSTEMD_SECCOMP': '0'}

    with mounting.NspawnActions(base_dir=target_userspace_info.path, binds=binds) as context:
        try:
            context.call(cmd, env=env)
        except CalledProcessError as e:
            raise StopActorExecutionError(
                "Failed to download target packages for the distribution swap workaround.",
                details={'details': str(e)},
            )


def _get_downloaded_rpms():
    return sorted(
        os.path.join(SWAP_DATA_DIR, name)
        for name in os.listdir(SWAP_DATA_DIR)
        if name.endswith('.rpm')
    )


def _generate_instructions(rpm_paths, packages_to_remove):
    """
    Build the dnf shell instructions swapping the packages in a single
    transaction: install the downloaded RPMs, remove the blockers, run.

    `install` MUST come first and list all local RPMs in one command: dnf shell
    only accepts local packages while no transaction job exists yet, else it
    rejects them (https://bugzilla.redhat.com/show_bug.cgi?id=1773483).
    Install-first also lets the RHEL replacements provide the capabilities of
    the removed packages, so the swap resolves as one atomic transaction.
    """
    lines = []
    if rpm_paths:
        lines.append('install {}'.format(' '.join(rpm_paths)))
    if packages_to_remove:
        lines.append('remove {}'.format(' '.join(packages_to_remove)))
    lines.append('run')
    return '\n'.join(lines) + '\n'


def _write_instructions(content):
    with open(DNF_SHELL_INSTRUCTIONS_PATH, 'w') as f:
        f.write(content)
    api.current_logger().debug(
        'Wrote distribution package swap dnf shell instructions to {}:\n{}'.format(
            DNF_SHELL_INSTRUCTIONS_PATH, content
        )
    )


def _register_workaround():
    api.produce(
        DNFWorkaround(
            display_name='distribution package swap',
            script_path=api.current_actor().get_common_tool_path('dnfshellswap'),
            script_args=[DNF_SHELL_INSTRUCTIONS_PATH, "--disablerepo='*'"],
        )
    )


def process():
    source_distro = get_source_distro_id()
    target_distro = get_target_distro_id()
    if source_distro == target_distro:
        return

    swap_config = _CONFIG.get((source_distro, target_distro))
    if not swap_config:
        api.current_logger().warning(
            "Could not find config for handling distro specific packages for {}->{} upgrade.".format(
                source_distro, target_distro
            )
        )
        return

    # Only el8 -> el9 removes Oracle's redhat-release here, early. el9 -> el10
    # does it during the main upgrade (see _OL_REDHAT_RELEASE_SWAP).
    if (source_distro, target_distro) == ("ol", "rhel") and get_target_major_version() == "9":
        swap_config = [_OL_REDHAT_RELEASE_SWAP] + list(swap_config)

    rpms_msg = next(api.consume(DistributionSignedRPM), None)
    if not rpms_msg:
        raise StopActorExecutionError("Did not receive DistributionSignedRPM message")
    installed_pkgs = {rpm.name for rpm in rpms_msg.items}

    active_swaps = _select_swaps(swap_config, installed_pkgs)
    if not active_swaps:
        return

    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    used_repos = list(api.consume(UsedTargetRepositories))
    if not target_userspace_info or not used_repos:
        api.current_logger().warning(
            'Cannot prepare the distribution package swap workaround: '
            'missing target userspace or target repositories information.'
        )
        return

    # de-duplicate while preserving order
    packages_to_download = set()
    for entry in active_swaps:
        packages_to_download.update(entry['install'])

    packages_to_remove = sorted(
        {pkg for entry in active_swaps for pkg in entry['remove'] if pkg in installed_pkgs}
    )

    _prepare_data_dir()
    _download_packages(packages_to_download, target_userspace_info, used_repos)

    rpm_paths = _get_downloaded_rpms()
    if not rpm_paths:
        raise StopActorExecutionError(
            "No packages were downloaded for the distribution swap workaround.",
            details={'details': 'Expected packages: {}'.format(', '.join(packages_to_download))},
        )

    _write_instructions(_generate_instructions(rpm_paths, packages_to_remove))
    _register_workaround()
