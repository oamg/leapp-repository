import warnings

no_dnf = False
no_dnf_warning_msg = "package `dnf` is unavailable"
try:
    import dnf
except ImportError:
    no_dnf = True
    warnings.warn(no_dnf_warning_msg, ImportWarning)


def get_modules():
    """
    Return info about all module streams as a list of libdnf.module.ModulePackage objects.
    """
    if no_dnf:
        return []

    base = dnf.Base()
    base.read_all_repos()
    base.fill_sack()

    module_base = dnf.module.module_base.ModuleBase(base)
    # this method is absent on RHEL 7, in which case there are no modules anyway
    if 'get_modules' not in dir(module_base):
        return []
    return module_base.get_modules('*')[0]


#TODO(drehak) multiple sack fills in this function - try to "recycle" the base
def get_enabled_modules():
    """
    Return currently enabled module streams as a list of libdnf.module.ModulePackage objects.
    """
    if no_dnf:
        return []

    base = dnf.Base()
    base.read_all_repos()
    base.fill_sack()

    modules = get_modules()
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
            # we transform the NEVRA string into a tuple
            rpm_ne, rpm_vra = rpm.split(':', 1)
            rpm_n = rpm_ne.rsplit('-', 1)[0]
            rpm_v, rpm_ra = rpm_vra.split('-', 1)
            rpm_r, rpm_a = rpm_ra.rsplit('.', 1)
            rpm_key = (rpm_n, rpm_v, rpm_r, rpm_a)
            # stream could be int or float, convert it to str just in case
            rpm_streams[rpm_key] = (module.getName(), str(module.getStream()))
    return rpm_streams
