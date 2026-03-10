"""
DEPRECATED: This module has been moved to leapp.libraries.common.dnflibs.dnfconfig

This shim will be removed in a future version. Please update imports to:
    from leapp.libraries.common.dnflibs import dnfconfig
    # or
    from leapp.libraries.common import dnflibs
"""

from leapp.libraries.common.dnflibs import dnfconfig as _dnfconfig
from leapp.utils.deprecation import deprecated


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfconfig module. '
    'Please update your imports to use the new location.'
))
def exclude_leapp_rpms(context, disable_plugins):
    """
    Ensure the leapp RPMs are excluded from any DNF transaction.

    This has to be called several times to ensure that our RPMs are not removed
    or updated (replaced) during the IPU. The action should happen inside
        - the target userspace container
        - on the host system
    So user will have to drop these packages from the exclude after the
    upgrade.
    """
    return _dnfconfig.exclude_leapp_rpms(context, disable_plugins)
