"""
DEPRECATED: This module has been moved to leapp.libraries.common.dnflibs.dnfmodule

This shim will be removed in a future version. Please update imports to:
    from leapp.libraries.common.dnflibs import dnfmodule
    # or
    from leapp.libraries.common import dnflibs
"""

from leapp.libraries.common.dnflibs import dnfmodule as _dnfmodule
from leapp.utils.deprecation import deprecated


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfmodule module. '
    'Please update your imports to use the new location.'
))
def get_modules(base=None):
    """
    Return info about all module streams as a list of libdnf.module.ModulePackage objects.
    """
    return _dnfmodule.get_modules(base)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfmodule module. '
    'Please update your imports to use the new location.'
))
def get_enabled_modules():
    """
    Return currently enabled module streams as a list of libdnf.module.ModulePackage objects.
    """
    return _dnfmodule.get_enabled_modules()


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfmodule module. '
    'Please update your imports to use the new location.'
))
def map_installed_rpms_to_modules():
    """
    Map installed modular packages to the module streams they come from.
    """
    return _dnfmodule.map_installed_rpms_to_modules()
