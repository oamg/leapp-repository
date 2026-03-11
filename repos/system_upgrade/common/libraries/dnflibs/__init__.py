"""
DNF-related libraries for the upgrade process.

This package consolidates DNF functionality previously scattered across:
- leapp.libraries.common.dnfconfig -> dnflibs.dnfconfig
- leapp.libraries.common.dnfplugin -> dnflibs.dnfplugin
- leapp.libraries.common.module -> dnflibs.dnfmodule
"""

# Import submodules for convenient access
from leapp.libraries.common.dnflibs import dnfconfig  # noqa: F401
from leapp.libraries.common.dnflibs import dnfmodule  # noqa: F401
from leapp.libraries.common.dnflibs import dnfplugin  # noqa: F401
