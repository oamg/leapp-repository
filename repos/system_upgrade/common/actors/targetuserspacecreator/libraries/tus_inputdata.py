"""
Input gathering and validation for the ``targetuserspacecreator`` actor.

Consumes every message the actor needs, applies three validation checks that
stop the upgrade when their preconditions are not met, and returns a single
plain value object (:class:`InputData`) carrying the raw messages plus a few
derived, frequently-needed values (the package list, the de-duplicated
copy-file list, and the ``skip_rhsm`` / ``nogpgcheck`` toggles).

Leaf module: imports only shared leapp libraries.
"""

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import rhsm
from leapp.libraries.common.gpg import is_nogpgcheck_set
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepositoryFile,
    PkgManagerInfo,
    RepositoriesFacts,
    RHELTargetRepository,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetOSInstallationImage,
    TargetRepositories,
    TargetUserSpacePreupgradeTasks
)
from leapp.utils.deprecation import suppress_deprecation

# Packages always installed into the target userspace, on top of whatever the
# TargetUserSpacePreupgradeTasks.install_rpms list requests
_DEFAULT_INSTALL_PKGS = {
    'dnf',
    'dnf-command(config-manager)',
    'dnf-command(download)',
    'util-linux',
}


class InputData:  # pylint: disable=too-many-arguments
    """
    Plain value object holding the validated actor inputs.

    Bundles the raw messages consumed by the actor together with a handful of
    derived values so downstream code receives a single, already-validated
    object instead of re-consuming and re-checking messages.
    """

    def __init__(self, storage_info, target_repositories, custom_repofiles,
                 rhsm_info, rhui_info, target_iso, repositories_facts,
                 pkg_manager_info, skip_rhsm, nogpgcheck, packages, copy_files):
        self.storage_info = storage_info
        self.target_repositories = target_repositories
        self.custom_repofiles = custom_repofiles
        self.rhsm_info = rhsm_info
        self.rhui_info = rhui_info
        self.target_iso = target_iso
        self.repositories_facts = repositories_facts
        self.pkg_manager_info = pkg_manager_info
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.packages = packages
        self.copy_files = copy_files


def _normalize_copy_files(copy_files):
    """
    Fill the destination of every CopyFile whose ``dst`` is empty with its ``src``.

    An empty ``dst`` means "copy to the same path as ``src``". Applying this
    convention once, here at the actor's input boundary, lets every downstream
    consumer rely on ``dst`` always being populated instead of re-implementing
    the ``dst or src`` fallback on each access. The given CopyFile objects are
    mutated in place.

    :param copy_files: CopyFile objects to normalize.
    :type copy_files: List[CopyFile]
    :returns: The same list that was passed in, for convenient chaining.
    :rtype: List[CopyFile]
    """
    for copy_file in copy_files:
        if not copy_file.dst:
            copy_file.dst = copy_file.src
    return copy_files


def _dedup_copy_files(copy_files):
    """
    De-duplicate CopyFile entries by their ``(src, dst)`` pair, preserving order.

    Expects ``dst`` to be already populated (see :func:`_normalize_copy_files`),
    so entries that differ only by an implicit versus explicit destination
    collapse into one.

    :param copy_files: CopyFile objects to de-duplicate.
    :type copy_files: List[CopyFile]
    :returns: A new list holding the first occurrence of each unique
        ``(src, dst)`` pair, in the original order.
    :rtype: List[CopyFile]
    """
    seen = set()
    result = []
    for copy_file in copy_files:
        key = (copy_file.src, copy_file.dst)
        if key in seen:
            continue
        seen.add(key)
        result.append(copy_file)
    return result


@suppress_deprecation(RHELTargetRepository)
def gather():
    """
    Consume and validate all actor inputs and return an :class:`InputData`.

    Reads every message the actor depends on, enforces the validation checks
    described below, builds the target-userspace package set (the built-in
    defaults plus whatever the preupgrade tasks request), and normalizes and
    de-duplicates the preupgrade copy-file list before wrapping everything in a
    single value object. When RHUIInfo is present, its client-setup copy files
    are normalized too (without de-duplication) so their destinations are
    always populated.

    :returns: The validated and derived actor inputs.
    :rtype: InputData
    :raises StopActorExecutionError: When no RHSMInfo message is available and
        RHSM is not being skipped.
    :raises StopActorExecutionError: When RHSM is being skipped yet an RHSMInfo
        message was produced (an inconsistent set of collected facts).
    :raises StopActorExecutionError: When no StorageInfo message is available.
    """
    storage_info = next(api.consume(StorageInfo), None)
    target_repositories = next(api.consume(TargetRepositories), None)
    rhsm_info = next(api.consume(RHSMInfo), None)
    rhui_info = next(api.consume(RHUIInfo), None)
    target_iso = next(api.consume(TargetOSInstallationImage), None)
    preupgrade_tasks = list(api.consume(TargetUserSpacePreupgradeTasks))
    repositories_facts = next(api.consume(RepositoriesFacts), None)
    pkg_manager_info = next(api.consume(PkgManagerInfo), None)
    custom_repofiles = list(api.consume(CustomTargetRepositoryFile))

    skip_rhsm = rhsm.skip_rhsm()

    if not rhsm_info and not skip_rhsm:
        # NOTE(pstodulk): seatbelt - this should not happen as the execution
        # should fail in earlier phases.
        raise StopActorExecutionError('Missing RHSM information.')

    if skip_rhsm and rhsm_info:
        # NOTE(pstodulk): this should not happen unless we made a bug in other
        # actors or found a reason for this state and forgot to update it.
        raise StopActorExecutionError(
            message='Inconsistent RHSM input.',
            details={
                'details': 'RHSM is set to be skipped (--no-rhsm / LEAPP_NO_RHSM)'
                           ' but RHSMInfo has been produced. This is an internal'
                           ' inconsistency in the collected facts.'
            }
        )

    if not storage_info:
        # NOTE(pstodulk): seatbelt, in practice the process would fail earlier
        raise StopActorExecutionError(
            message='Missing storage information.',
            details={'details': 'No StorageInfo message has been produced.'}
        )

    raw_copy_files = []
    # Copy the module-level default set so repeated gather() calls do not
    # accumulate packages into the shared default.
    packages = set(_DEFAULT_INSTALL_PKGS)
    for task in preupgrade_tasks:
        packages |= set(task.install_rpms)
        raw_copy_files.extend(task.copy_files)

    copy_files = _dedup_copy_files(_normalize_copy_files(raw_copy_files))

    # Normalize the RHUI client-setup copy files too, so tus_rhui can rely on a
    # populated dst without re-applying the dst-or-src convention per access.
    if rhui_info:
        setup = rhui_info.target_client_setup_info
        _normalize_copy_files(setup.preinstall_tasks.files_to_copy_into_overlay)
        _normalize_copy_files(setup.postinstall_tasks.files_to_copy)

    # TODO do we want this in the data? makes mocking a little easier maybe
    nogpgcheck = is_nogpgcheck_set()

    return InputData(
        storage_info=storage_info,
        target_repositories=target_repositories,
        custom_repofiles=custom_repofiles,
        rhsm_info=rhsm_info,
        rhui_info=rhui_info,
        target_iso=target_iso,
        repositories_facts=repositories_facts,
        pkg_manager_info=pkg_manager_info,
        skip_rhsm=skip_rhsm,
        nogpgcheck=nogpgcheck,
        packages=packages,
        copy_files=copy_files,
    )
