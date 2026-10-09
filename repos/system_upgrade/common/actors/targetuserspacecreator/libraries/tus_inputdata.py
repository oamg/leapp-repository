"""
Input gathering and validation for the ``targetuserspacecreator`` actor (§2).

Consumes every message the actor needs, applies the three hard-stop validation
rules, and returns a single plain value object (:class:`InputData`) carrying the
raw messages plus a few derived, frequently-needed values (the package list, the
de-duplicated copy-file list, and the ``skip_rhsm`` / ``nogpgcheck`` toggles).

Leaf module: imports only shared leapp libraries and ``tus_constants``.
"""

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import rhsm
from leapp.libraries.common.gpg import is_nogpgcheck_set
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepositoryFile,
    PkgManagerInfo,
    RepositoriesFacts,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetOSInstallationImage,
    TargetRepositories,
    TargetUserSpacePreupgradeTasks,
    XFSPresence,
)

# Packages always installed into the target userspace, on top of whatever the
# TargetUserSpacePreupgradeTasks.install_rpms list requests
_DEFAULT_INSTALL_PKGS = {
    'dnf',
    'dnf-command(config-manager)',
    'dnf-command(download)',
    'util-linux',
}


class InputData(object):
    """Plain value object holding the validated actor inputs."""

    def __init__(self, storage_info, target_repositories, custom_repofiles,
                 rhsm_info, rhui_info, target_iso, preupgrade_tasks,
                 xfs_presence, repositories_facts, pkg_manager_info,
                 skip_rhsm, nogpgcheck, packages, copy_files):
        self.storage_info = storage_info
        self.target_repositories = target_repositories
        self.custom_repofiles = custom_repofiles
        self.rhsm_info = rhsm_info
        self.rhui_info = rhui_info
        self.target_iso = target_iso
        self.preupgrade_tasks = preupgrade_tasks
        self.xfs_presence = xfs_presence
        self.repositories_facts = repositories_facts
        self.pkg_manager_info = pkg_manager_info
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.packages = packages
        self.copy_files = copy_files


def _dedup_copy_files(copy_files):
    """De-duplicate CopyFile entries by their (src, dst) pair, preserving order."""
    seen = set()
    result = []
    for copy_file in copy_files:
        # TODO this does not consider that if dst == None then dst = src
        key = (copy_file.src, copy_file.dst)
        if key in seen:
            continue
        seen.add(key)
        result.append(copy_file)
    return result


def gather():
    """
    Consume and validate all inputs; return an :class:`InputData`.

    :raises StopActorExecutionError: on any of the three §2 hard-stop rules.
    """
    storage_info = next(api.consume(StorageInfo), None)
    target_repositories = next(api.consume(TargetRepositories), None)
    rhsm_info = next(api.consume(RHSMInfo), None)
    rhui_info = next(api.consume(RHUIInfo), None)
    target_iso = next(api.consume(TargetOSInstallationImage), None)
    preupgrade_tasks = list(api.consume(TargetUserSpacePreupgradeTasks))
    ### FIXME: rename to xfs_info to meet with naming in other libs
    ### FIXME orig code uses XFSPresence() as default
    xfs_presence = next(api.consume(XFSPresence), None)
    repositories_facts = next(api.consume(RepositoriesFacts), None)
    pkg_manager_info = next(api.consume(PkgManagerInfo), None)
    custom_repofiles = list(api.consume(CustomTargetRepositoryFile))

    skip_rhsm = rhsm.skip_rhsm()

    # Hard-stop #1: no RHSMInfo while RHSM is not being skipped.
    if not rhsm_info and not skip_rhsm:
        # FIXME orig code has StopActorExecution and log
        raise StopActorExecutionError(
            message='Missing RHSM information.',
            details={
                'hint': 'The system does not seem to be registered. Register the'
                        ' system using subscription-manager, or run leapp with'
                        ' the --no-rhsm option if you intend to use custom'
                        ' repositories instead.'
            }
        )

    # Hard-stop #2: RHSM is being skipped but RHSMInfo is present (inconsistent).
    # FIXME: take a look, originally just a log, I think it's covered by error
    # somewhere else (earlier actor?) now..
    # FIXME: check also rest of arts
    if skip_rhsm and rhsm_info:
        raise StopActorExecutionError(
            message='Inconsistent RHSM input.',
            details={
                'details': 'RHSM is set to be skipped (--no-rhsm / LEAPP_NO_RHSM)'
                           ' but RHSMInfo has been produced. This is an internal'
                           ' inconsistency in the collected facts.'
            }
        )

    # Hard-stop #3: no StorageInfo.
    if not storage_info:
        raise StopActorExecutionError(
            message='Missing storage information.',
            details={'details': 'No StorageInfo message has been produced.'}
        )

    raw_copy_files = []
    packages = _DEFAULT_INSTALL_PKGS
    for task in preupgrade_tasks:
        packages |= task.install_rpms
        raw_copy_files.append(task.copy_files)

    copy_files = _dedup_copy_files(raw_copy_files)

    # TODO do we want this in the data? makes mocking a little easier maybe
    nogpgcheck = is_nogpgcheck_set()

    return InputData(
        storage_info=storage_info,
        target_repositories=target_repositories,
        custom_repofiles=custom_repofiles,
        rhsm_info=rhsm_info,
        rhui_info=rhui_info,
        target_iso=target_iso,
        preupgrade_tasks=preupgrade_tasks,
        xfs_presence=xfs_presence,
        repositories_facts=repositories_facts,
        pkg_manager_info=pkg_manager_info,
        skip_rhsm=skip_rhsm,
        nogpgcheck=nogpgcheck,
        packages=packages,
        copy_files=copy_files,
    )
