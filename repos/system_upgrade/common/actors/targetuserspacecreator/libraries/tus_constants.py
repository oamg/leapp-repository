"""
Shared, dependency-free constants and tiny pure helpers for the
``targetuserspacecreator`` actor.

This module sits at the very bottom of the actor's import DAG: it imports
nothing actor-side, so any other ``tus_*`` module may import it without risking
an import cycle. Keep it free of side effects and of imports from sibling
``tus_*`` modules.
"""

from leapp.libraries.common.config.version import get_major_version


def common_dnf_flags(target_version, skip_rhsm):
    """
    Build the dnf flags shared by the userspace install (§10) and the RHUI
    client swap (§13 R5).

    :param target_version: Target OS release version to pass to dnf.
    :param skip_rhsm: Whether subscription-manager is being skipped.
    :return: List of dnf command-line arguments.
    """
    flags = [
        '--setopt=module_platform_id=platform:el{}'.format(get_major_version(target_version)),
        '--setopt=keepcache=1',
        '--releasever', target_version,
    ]
    if skip_rhsm:
        flags += ['--disableplugin', 'subscription-manager']
    return flags
