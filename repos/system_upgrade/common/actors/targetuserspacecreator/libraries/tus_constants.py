"""
Shared, dependency-free constants and tiny pure helpers for the
``targetuserspacecreator`` actor.

This module sits at the very bottom of the actor's import DAG: it imports
nothing actor-side, so any other ``tus_*`` module may import it without risking
an import cycle. Keep it free of side effects and of imports from sibling
``tus_*`` modules.
"""

# Packages always installed into the target userspace, on top of whatever the
# TargetUserSpacePreupgradeTasks.install_rpms list requests (§2).
DEFAULT_INSTALL_PKGS = [
    'dnf',
    'dnf-command(config-manager)',
    'dnf-command(download)',
    'util-linux',
]

# Default container root; overridable via LEAPP_CONTAINER_ROOT (§12).
DEFAULT_CONTAINER_ROOT = '/var/lib/leapp'

# Name of the target userspace directory inside the container root. The target
# major version is substituted in at runtime (§1).
USERSPACE_DIRNAME_TEMPLATE = 'el{target_major}userspace'


def common_dnf_flags(target_major, releasever, skip_rhsm):
    """
    Build the dnf flags shared by the userspace install (§10) and the RHUI
    client swap (§13 R5).

    :param target_major: Target OS major version (e.g. ``'9'``).
    :param releasever: Target releasever to pass to dnf.
    :param skip_rhsm: Whether subscription-manager is being skipped.
    :return: List of dnf command-line arguments.
    """
    flags = [
        '--setopt=module_platform_id=platform:el{}'.format(target_major),
        '--setopt=keepcache=1',
        '--releasever', releasever,
    ]
    if skip_rhsm:
        flags += ['--disableplugin', 'subscription-manager']
    return flags
