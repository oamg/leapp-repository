"""
Shared, dependency-free constants and small pure helpers for the ``targetuserspacecreator`` actor.

This module intentionally imports nothing from the sibling ``tus_*`` modules, so any of them may import it without
creating an import cycle. Keep it free of side effects and of such sibling imports.
"""

from leapp.libraries.common.config.version import get_major_version


def common_dnf_flags(target_version, skip_rhsm):
    """
    Build the common dnf command-line flags shared by the target userspace install and the RHUI client swap.

    The returned flags set the module platform id for the target major version, keep the dnf cache, and pin the
    release version. When subscription-manager is being skipped, its dnf plugin is disabled as well.

    :param target_version: Target OS release version passed to dnf as ``--releasever``.
    :type target_version: str
    :param skip_rhsm: Whether subscription-manager (and its dnf plugin) is being skipped.
    :type skip_rhsm: bool
    :returns: The dnf command-line arguments to be reused by callers.
    :rtype: List[str]
    """
    flags = [
        '--setopt=module_platform_id=platform:el{}'.format(get_major_version(target_version)),
        '--setopt=keepcache=1',
        '--releasever', target_version,
    ]
    if skip_rhsm:
        flags += ['--disableplugin', 'subscription-manager']
    return flags
