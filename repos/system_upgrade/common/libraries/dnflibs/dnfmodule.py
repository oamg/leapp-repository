import warnings

from leapp.libraries.common.dnflibs import create_dnf_base

try:
    import dnf
except ImportError:
    dnf = None
    warnings.warn('Could not import the `dnf` python module.', ImportWarning)

try:
    import hawkey
except ImportError:
    hawkey = None
    warnings.warn('Could not import the `hawkey` python module.', ImportWarning)


def get_modules(base=None):
    """
    Return info about all module streams as a list of libdnf.module.ModulePackage objects.

    The function return an empty list if the DNF python module is not present.

    :param base: If it is set, use it instead of creating a new one.
    :type base: dnf.Base

    .. seealso::
        :func:`create_dnf_base` for exceptions raised when creating dnf.Base
    """
    if not dnf:
        return []
    if not base:
        base = create_dnf_base()

    module_base = dnf.module.module_base.ModuleBase(base)
    # this method is absent on RHEL 7, in which case there are no modules anyway
    # note the method could be removed in future as well - so keep the check
    if not hasattr(module_base, 'get_modules'):
        return []
    return module_base.get_modules('*')[0]


def get_enabled_modules():
    """
    Return currently enabled module streams as a list of libdnf.module.ModulePackage objects.

    The function return an empty list if the DNF python module is not present.

    .. seealso::
        :func:`get_modules` for exceptions raised during module discovery.
        :func:`create_dnf_base` for exceptions raised when creating dnf.Base
    """
    if not dnf:
        return []

    base = create_dnf_base()
    modules = get_modules(base)

    # if modules are not supported (RHEL 7), base.sack._moduleContainer won't exist
    # luckily in that case modules are empty and the element won't even be accessed
    return [m for m in modules if base.sack._moduleContainer.isEnabled(m)]


def map_installed_rpms_to_modules():
    """
    Map installed modular packages to the module streams they come from.

    :returns: Mapping of RPM NVRA tuples to (module_name, stream) tuples
    :rtype: dict

    .. seealso::
        :func:`get_modules` for exceptions raised during module discovery.
    """
    modules = get_modules()
    # empty on RHEL 7 because of no modules
    if not modules:
        return {}
    # create a reverse mapping from the RPMS to module streams
    # key: tuple of 4 strings representing a NVRA (name, version, release, arch) of an RPM
    # value: tuple of 2 strings representing a module and its stream
    rpm_streams = {}
    for module in modules:
        for rpm in module.getArtifacts():
            nevra = hawkey.split_nevra(rpm)
            rpm_key = (nevra.name, nevra.version, nevra.release, nevra.arch)
            rpm_streams[rpm_key] = (module.getName(), module.getStream())
    return rpm_streams
