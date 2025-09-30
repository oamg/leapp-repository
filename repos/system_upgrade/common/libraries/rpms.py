from leapp.libraries import stdlib
from leapp.libraries.common.config.version import get_source_major_version
from leapp.models import InstalledRPM


class LeappComponents(object):
    """
    Supported component values to be used with get_packages_function:
    * FRAMEWORK - the core of the leapp project: the leapp executable and
      associated leapp libraries
    * REPOSITORY - the leapp-repository project
    * COCKPIT - the cockpit-leapp project
    * TOOLS - miscellaneous tooling like snactor
    """
    FRAMEWORK = 'framework'
    REPOSITORY = 'repository'
    COCKPIT = 'cockpit'
    TOOLS = 'tools'


# NOTE: need to keep package for dropped upgrade paths so peseventsscanner can drop
# related PES events
_LEAPP_PACKAGES_MAP = {
    LeappComponents.FRAMEWORK: {
        "7": {"pkgs": ["leapp", "python2-leapp"], "deps": ["leapp-deps"]},
        "8": {"pkgs": ["leapp", "python3-leapp"], "deps": ["leapp-deps"]},
        "9": {"pkgs": ["leapp", "python3-leapp"], "deps": ["leapp-deps"]},
    },
    LeappComponents.REPOSITORY: {
        "7": {
            "pkgs": ["leapp-upgrade-el7toel8"],
            "deps": ["leapp-upgrade-el7toel8-deps"],
        },
        "8": {
            "pkgs": ["leapp-upgrade-el8toel9", "leapp-upgrade-el8toel9-fapolicyd"],
            "deps": ["leapp-upgrade-el8toel9-deps"],
        },
        "9": {
            "pkgs": ["leapp-upgrade-el9toel10", "leapp-upgrade-el9toel10-fapolicyd"],
            "deps": ["leapp-upgrade-el9toel10-deps"],
        },
    },
    LeappComponents.COCKPIT: {
        "7": {"pkgs": ["cockpit-leapp"]},
        "8": {"pkgs": ["cockpit-leapp"]},
        "9": {"pkgs": ["cockpit-leapp"]},
    },
    LeappComponents.TOOLS: {
        "7": {"pkgs": ["snactor"]},
        "8": {"pkgs": ["snactor"]},
        "9": {"pkgs": ["snactor"]},
    },
}

GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS = frozenset((LeappComponents.FRAMEWORK,
                                                   LeappComponents.REPOSITORY,
                                                   LeappComponents.TOOLS))


def get_installed_rpms():
    rpm_cmd = [
        '/bin/rpm',
        '-qa',
        '--queryformat',
        r'%{NAME}|%{VERSION}|%{RELEASE}|%|EPOCH?{%{EPOCH}}:{0}||%|PACKAGER?{%{PACKAGER}}:{(none)}||%|'
        r'ARCH?{%{ARCH}}:{}||%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{(none)}|}|\n'
    ]
    try:
        return stdlib.run(rpm_cmd, split=True)['stdout']
    except stdlib.CalledProcessError as err:
        error = 'Execution of {CMD} returned {RC}. Unable to find installed packages.'.format(CMD=err.command,
                                                                                              RC=err.exit_code)
        stdlib.api.current_logger().error(error)
        return []


def create_lookup(model, field, keys, context=stdlib.api):
    """
    Create a lookup set from one of the model fields.

    :param model: model class
    :param field: model field, its value will be taken for lookup data
    :param key: property of the field's data that will be used to build a resulting set
    :param context: context of the execution
    """
    data = getattr(next((m for m in context.consume(model)), model()), field)
    try:
        return {tuple(getattr(obj, key) for key in keys) for obj in data} if data else set()
    except TypeError:
        # data is not iterable, not lookup can be built
        stdlib.api.current_logger().error(
                "{model}.{field}.{keys} is not iterable, can't build lookup".format(
                    model=model, field=field, keys=keys))
        return set()


def has_package(model, package_name, arch=None, version=None, release=None, context=stdlib.api):
    """
    Expects a DistributionSignedRPM or ThirdPartyRPM model.
    Can be useful in cases like a quick item presence check, ex. check in actor that
    a certain package is installed.

    :param model: model class
    :param package_name: package to be checked
    :param arch: filter by architecture. None means all arches.
    :param version: filter by version. None means all versions.
    :param release: filter by release. None means all releases.
    """
    if not (isinstance(model, type) and issubclass(model, InstalledRPM)):
        return False
    keys = ['name']
    if arch:
        keys.append('arch')
    if version:
        keys.append('version')
    if release:
        keys.append('release')

    attributes = [package_name]
    attributes += [attr for attr in (arch, version, release) if attr is not None]
    rpm_lookup = create_lookup(model, field='items', keys=keys, context=context)
    return tuple(attributes) in rpm_lookup


def _read_rpm_modifications(config):
    """
    Ask RPM database whether the configuration file was modified.

    :param config: a config file to check
    """
    try:
        return stdlib.run(['rpm', '-Vf', config], split=True, checked=False)['stdout']
    except OSError as err:
        error = 'Failed to check the modification status of the file {}: {}'.format(config, str(err))
        stdlib.api.current_logger().error(error)
        return []


def _parse_config_modification(data, config):
    """
    Handle the output of rpm verify command to figure out if configuration file was modified.

    :param data: output of the rpm verify
    :param config: a config file to check
    """

    # First assume it is not modified -- empty data says it is not modified
    modified = False
    for line in data:
        parts = line.split(' ')
        # The last part of the line is the actual file we care for
        if parts[-1] == config:
            # First part contains information, if the size and digest differ
            if '5' in parts[0] or 'S' in parts[0]:
                modified = True
        # Ignore any other files lurking here

    return modified


def check_file_modification(config):
    """
    Check if the given configuration file tracked by RPM was modified

    This is useful when figuring out if the file will be replaced by the rpm on the upgrade
    or we need to take care of the upgrade manually.

    :param config: The configuration file to check
    """
    output = _read_rpm_modifications(config)
    return _parse_config_modification(output, config)


def _get_leapp_packages_of_type(major_version, component, type_='pkgs'):
    """
    Private implementation of get_leapp_packages() and get_leapp_deps_packages().

    :param major_version: Same as for :func:`get_leapp_packages` and
        :func:`get_leapp_deps_packages`
    :param component: Same as for :func:`get_leapp_packages` and :func:`get_leapp_deps_packages`
    :param type_: Either "pkgs" or "deps".  Determines which set of packages we're looking for.
        Corresponds to the keys in the `_LEAPP_PACKAGES_MAP`.

    Retrieving the set of leapp and leapp-deps packages only differs in which key is used to
    retrieve the packages from _LEAPP_PACKAGES_MAP.  This function abstracts that difference.
    """
    res = set()

    major_versions = [major_version] if isinstance(major_version, str) else major_version
    if not major_versions:
        # No major_version of interest specified -> treat as if only current source system version
        # requested
        major_versions = [get_source_major_version()]

    components = [component] if isinstance(component, str) else component
    if not components:
        error_msg = ("At least one component must be specified when calling this"
                     " function, available choices are {choices}".format(
                         choices=sorted(_LEAPP_PACKAGES_MAP.keys()))
                     )
        raise ValueError(error_msg)

    for comp in components:
        for a_major_version in major_versions:
            if comp not in _LEAPP_PACKAGES_MAP:
                error_msg = "The requested component {comp} is unknown, available choices are {choices}".format(
                        comp=component, choices=sorted(_LEAPP_PACKAGES_MAP.keys()))
                raise ValueError(error_msg)

            if a_major_version not in _LEAPP_PACKAGES_MAP[comp]:
                error_msg = "The requested major_version {ver} is unknown, available choices are {choices}".format(
                        ver=a_major_version, choices=sorted(_LEAPP_PACKAGES_MAP[comp].keys()))
                raise ValueError(error_msg)

            # All went well otherwise, get the data
            res.update(_LEAPP_PACKAGES_MAP[comp][a_major_version].get(type_, []))

    return sorted(res)


def get_leapp_packages(major_version=None, component=GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS):
    """
    Get list of leapp packages.

    :param major_version: a list or string specifying major_versions. If not defined then current
        system_version will be used.
    :param component: a list or a single enum value specifying leapp components
        (use enum :class: LeappComponents) If defined then only packages related to the specific
        component(s) will be returned.
        The default set of components is in `GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS` and
        simple modifications of the default can be achieved with code like:

        .. code-block:: python
            get_leapp_packages(
                component=GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS.difference(
                    [LeappComponents.TOOLS]
            ))

    :raises ValueError: if a requested component or major_version doesn't exist.

    .. note::
        Call :func:`get_leapp_dep_packages` as well if you also need the deps metapackages.
        Those packages determine which RPMs need to be installed for leapp to function.
        They aren't just Requires on the base leapp and leapp-repository RPMs because they
        need to be switched from the old system_version's to the new ones at a different
        point in the upgrade than the base RPMs.
    """
    return _get_leapp_packages_of_type(major_version, component, type_="pkgs")


def get_leapp_dep_packages(major_version=None, component=GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS):
    """
    Get list of leapp dep metapackages.

    :param major_version: a list or string specifying major_versions. If not defined then current
        system_version will be used.
    :param component: a list or a single enum value specifying leapp components
        (use enum :class: LeappComponents) If defined then only packages related to the specific
        component(s) will be returned.
        The default set of components is in `GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS` and
        simple modifications of the default can be achieved with code like:

        .. code-block:: python
            get_leapp_packages(
                component=GET_LEAPP_PACKAGES_DEFAULT_COMPONENTS.difference(
                    [LeappComponents.TOOLS]
            ))
    :raises ValueError: if a requested component or major_version doesn't exist.
    """
    return _get_leapp_packages_of_type(major_version, component, type_="deps")
