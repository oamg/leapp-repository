"""
DNF-related libraries for the upgrade process.

This package consolidates DNF functionality previously scattered across:
- leapp.libraries.common.dnfconfig -> dnflibs.dnfconfig
- leapp.libraries.common.dnfplugin -> dnflibs.dnfplugin
- leapp.libraries.common.module -> dnflibs.dnfmodule
"""

from leapp.exceptions import StopActorExecutionError


class DNFError(StopActorExecutionError):
    """
    Generic exception inherited by all DNF errors raised in dnflibs libraries.
    """
