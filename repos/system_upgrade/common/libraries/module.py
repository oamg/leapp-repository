import warnings

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


def _create_or_get_dnf_base(base=None):
    if not base:
        base = dnf.Base()
        base.init_plugins()
        base.read_all_repos()
        # configure plugins after the repositories are loaded
        # e.g. the amazon-id plugin requires loaded repositories
        # for the proper configuration.
        base.configure_plugins()
        base.fill_sack()
    return base


def get_modules(base=None):
    """
    Return info about all module streams as a list of libdnf.module.ModulePackage objects.
    """
    if not dnf:
        return []
    base = _create_or_get_dnf_base(base)

    module_base = dnf.module.module_base.ModuleBase(base)
    # this method is absent on RHEL 7, in which case there are no modules anyway
    if not hasattr(module_base, 'get_modules'):
        return []
    return module_base.get_modules('*')[0]


def get_enabled_modules():
    """
    Return currently enabled module streams as a list of libdnf.module.ModulePackage objects.
    """
    if not dnf:
        return []

    base = _create_or_get_dnf_base()
    modules = get_modules(base)

    # if modules are not supported (RHEL 7), base.sack._moduleContainer won't exist
    # luckily in that case modules are empty and the element won't even be accessed
    return [m for m in modules if base.sack._moduleContainer.isEnabled(m)]


def map_installed_rpms_to_modules():
    """
    Map installed modular packages to the module streams they come from.
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
