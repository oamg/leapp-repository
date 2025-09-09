import operator
import re

import six

from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.stdlib import api
from leapp.utils.deprecation import deprecated

OP_MAP = {
    '>': operator.gt,
    '>=': operator.ge,
    '<': operator.lt,
    '<=': operator.le
}

_SUPPORTED_VERSIONS = {
    '8': {'rhel': ['8.10'], 'rhel-saphana': ['8.10']},
    '9': {'rhel': ['9.6'], 'rhel-saphana': ['9.6']},
}


def get_major_version(version):
    """
    Return the major version from the given version string.

    Versioning schema: MAJOR.MINOR.PATCH
    It doesn't matter how many dots are present. Everything until the first dot is returned. E.g.:
       8.1.0 => 8
       7.9   => 7
       7     => 7

    :param str version: The version string according to the versioning schema described.
    :rtype: str
    :returns: The major version from the given version string.
    """
    return version.split('.')[0]


def get_source_version():
    """
    Return the version of the source system.

    :rtype: str
    :returns: The version of the source system.
    """
    return api.current_actor().configuration.version.source


def get_source_major_version():
    """
    Return the major version of the source (original) system.

    For more details about about the versioning schema see :func:`get_major_version`.

    :rtype: str
    :returns: The major version of the source system.
    """
    return get_major_version(get_source_version())


def get_target_version():
    """
    Return the version of the target system.

    :rtype: str
    :returns: The version of the target system.
    """
    return api.current_actor().configuration.version.target


def get_target_major_version():
    """
    Return the major version of the target system.

    For more details about about the versioning schema see :func:`get_major_version`.

    :rtype: str
    :returns: The major version of the target system.
    """
    return get_major_version(get_target_version())


class _SupportedVersionsDict(dict):
    """
    Class for _SUPPORTED_VERSIONS lazy evaluation until ipuworkflowconfig actor data
    is ready.
    """

    def __init__(self):  # pylint: disable=W0231
        self.data = {}

    def _feed_supported_versions(self):
        major = get_source_major_version()
        if major not in _SUPPORTED_VERSIONS:
            raise KeyError('{} is not a supported source version of RHEL'.format(major))
        self.data = _SUPPORTED_VERSIONS[major]

    def __getitem__(self, key):
        self._feed_supported_versions()
        return self.data[key]

    def __iter__(self):
        self._feed_supported_versions()
        for d in self.data:
            yield d

    def __repr__(self):
        self._feed_supported_versions()
        return repr(self.data)

    def __contains__(self, x):
        self._feed_supported_versions()
        return x in self.data

    def __len__(self):
        self._feed_supported_versions()
        return len(self.data)

    def __str__(self):
        self._feed_supported_versions()
        return str(self.data)


SUPPORTED_VERSIONS = _SupportedVersionsDict()
"""
Deprecated since 2025-03-31.

Use is_supported_version(), or IPUConfig.supported_upgrade_paths to check what source
versions are supported for the current (release, flavour).
"""


def _version_to_tuple(version):
    """Converts the version string ``major.minor`` to ``(major, minor)`` int tuple."""
    major, minor = version.split('.')
    return (int(major), int(minor))


def _validate_versions(versions):
    """Raise ``ValueError`` if provided versions are not strings in the form ``<integer>.<integer>``."""
    version_format_regex = re.compile(r'^([1-9]\d*)\.(\d+)$')
    for version in versions:
        if not re.match(version_format_regex, version):
            raise ValueError("Versions have to be in the form of '<integer>.<integer>' "
                             "but provided was '{}'".format(versions))


def _are_comparison_operators_used(versions):
    """Return ``True`` if provided versions are list of strings without comparison operators."""
    return not all(len(v.split()) == 1 for v in versions)


def _cmp_versions(versions):
    """Return ``True`` if provided versions are list of strings with comparison operators."""
    split = [v.split() for v in versions]
    if not all(len(s) == 2 for s in split):
        return False

    return all(s[0] in OP_MAP for s in split)


def _autocorrect_centos_version(version_to_correct):
    version_cfg = api.current_actor().configuration.version
    if version_to_correct == version_cfg.source:
        version_to_correct = version_cfg.virtual_source_version
    elif version_to_correct == version_cfg.target:
        version_to_correct = version_cfg.virtual_target_version
    return version_to_correct


def matches_version(match_list, detected):
    """
    Check if the `detected` version meets the criteria specified in `match_list`.

    :param match_list: specification of versions to check against
    :type match_list: list or tuple of strings in one of the two following forms:
                      ``['>'|'>='|'<'|'<='] <integer>.<integer>`` form, where elements are ANDed,
                      meaning that ``['>= 7.6', '< 7.8']`` would match for ``'7.6'``, and ``'7,7'`` only.
                      ``<integer>.<integer>`` form, where elements are ORed, meaning that
                      ``['7.6', '7.7']`` would match for ``'7.6'``, and ``'7,7'`` only.
                      These two forms cannot be mixed, otherwise ``ValueError`` is raised.
    :param detected: detected version
    :type detected: string in the form ``<integer>.<integer>``
    :return: ``True`` if `detected` value matches one of the values in `match_list`, ``False`` otherwise
    :rtype: bool
    """
    if not isinstance(match_list, (list, tuple)):
        raise TypeError("Versions to check against have to be a list or tuple "
                        "but provided was {}: '{}'".format(type(match_list), match_list))
    if not all(isinstance(e, six.string_types) for e in match_list):
        raise TypeError("Versions to check against have to be a list or tuple of strings "
                        "but provided was {}: '{}'".format([type(e) for e in match_list], match_list))
    if not isinstance(detected, six.string_types):
        raise TypeError("Detected version has to be a string "
                        "but provided was {}: '{}'".format(type(detected), detected))

    # If we are on CentOS, and we are provided with a version of the form MAJOR, try to correct
    # the version into MAJOR.MINOR using virtual versions
    if api.current_actor().configuration.os_release.release_id == 'centos':
        new_detected = _autocorrect_centos_version(detected)
        # We might have a matchlist ['> 8', '<= 9'] that, e.g., results from blindly using source/target versions
        # to make a matchlist. Our `detected` version might be some fixed string, e.g., `9.1`. So we need to
        # also autocorrect the matchlist. Due to how autocorrection works, no changes are done to matchlist
        # parts that contain full versions.
        new_matchlist = []
        for predicate in match_list:
            if ' ' in predicate:
                op, version = predicate.split(' ', 1)
                version = _autocorrect_centos_version(version)
                new_matchlist.append('{} {}'.format(op, version))
            else:
                version = _autocorrect_centos_version(predicate)
                new_matchlist.append(version)

        msg = 'Performed autocorrection from matches_version(%s, %s) to matches_version(%s, %s)'
        api.current_logger().debug(msg, match_list, detected, new_matchlist, new_detected)

        match_list = new_matchlist
        detected = new_detected

    _validate_versions([detected])

    if not _are_comparison_operators_used(match_list):
        # match_list = ['7.6', '7.7', '7.8', '7.9']
        _validate_versions(match_list)
        return detected in match_list

    if _cmp_versions(match_list):
        detected = _version_to_tuple(detected)
        # match_list = ['>= 7.6', '< 7.10']
        _validate_versions([s.split()[1] for s in match_list])
        for match in match_list:
            op, ver = match.split()
            ver = _version_to_tuple(ver)
            if not OP_MAP[op](detected, ver):
                return False
        return True

    raise ValueError("Versions have to be a list or tuple of strings in the form "
                     "'['>'|'>='|'<'|'<='] <integer>.<integer>' or "
                     "'<integer>.<integer>' but provided was '{}'".format(match_list))


def matches_source_version(*match_list):
    """
    Check if one of provided source versions matches the configured one.

    :param match_list: specification of versions to check against
    :type match_list: strings, for details see argument ``match_list`` of function :func:`matches_version`.
    """
    return matches_version(match_list, get_source_version())


def matches_target_version(*match_list):
    """
    Check if one of provided target versions matches the configured one.

    :param match_list: specification of versions to check against
    :type match_list: strings, for details see argument ``match_list`` of function :func:`matches_version`.
    """
    return matches_version(match_list, get_target_version())


def matches_release(allowed_releases, release):
    """
    Check if the given `release` is allowed to upgrade based in `allowed_releases`.

    :param allowed_releases: All supported releases
    :type allowed_releases: list or dict
    :param release: release name to be checked
    :type release: string
    :return: ``True`` if `release` value matches one of the values in `allowed_releases`, ``False`` otherwise
    :rtype: bool
    """
    if not (release and allowed_releases):
        return False

    return release in allowed_releases


def current_version():
    """
    Return the current Linux release and version.

    :return: The tuple contains release name and version value.
    :rtype: (string, string)
    """
    release = api.current_actor().configuration.os_release
    return release.release_id, release.version_id


def is_default_flavour():
    """
    Check if the current system uses the default upgrade path.

    :return: `True` if this upgrade process is using the default upgrade path and `False` otherwise.
    :rtype: bool
    """
    return api.current_actor().configuration.flavour == 'default'


def is_sap_hana_flavour():
    """
    Check if the current system needs to use the SAP HANA upgrade path.

    :return: `True` if this upgrade process is using the SAP HANA upgrade path and `False` otherwise.
    :rtype: bool
    """
    return api.current_actor().configuration.flavour == 'saphana'


@deprecated(since='2025-08-14', message=(
    'RHEL-ALT reached EOL years ago and it is connected just to RHEL 7 systems.'
    'As such the function is useless nowadays and will return always False.'
    'The function is going to be removed in the next leapp-repository release.'
))
def is_rhel_alt():
    """
    Check if the current system is RHEL-ALT or not (only for RHEL 7)

    The function is valid only for the RHEL 7 systems. On RHEL 8+ systems
    returns always False.

    :return: `True` if the current system is RHEL-ALT and `False` otherwise.
    :rtype: bool
    """

    if get_source_major_version() != '7':
        return False
    conf = api.current_actor().configuration
    # rhel-alt is rhel 7 with kernel 4.x - there is not better detection...
    return conf.os_release.release_id == 'rhel' and conf.kernel[0] == '4'


@deprecated(since='2023-08-15', message='This information is now provided by KernelInfo message.')
def is_rhel_realtime():
    """
    Check whether the original system is RHEL Real Time.

    Currently the check is based on the release of the original booted kernel.
    In case of RHEL, we are sure the release contains the ".rt" string and
    non-realtime kernels don't. Let's use this minimalistic check for now.
    In future, we could detect whether the system is preemptive or not based
    on properties of the kernel (e.g. uname -a tells that information).

    :return: `True` if the orig system is RHEL RT and `False` otherwise.
    :rtype: bool
    """
    conf = api.current_actor().configuration
    if conf.os_release.release_id != 'rhel':
        return False

    kernel_type = kernel_lib.determine_kernel_type_from_uname(get_source_version(), conf.kernel)
    return kernel_type == kernel_lib.KernelType.REALTIME


def is_supported_version():
    """
    Verify if the current system version is supported for the upgrade.

    :return: `True` if the current version is supported and `False` otherwise.
    :rtype: bool
    """
    source_version = get_source_version()
    supported_upgrade_paths = api.current_actor().configuration.supported_upgrade_paths

    # Check if there are any paths defined from the current source_version. If not,
    # the upgrade version is unsupported
    for ipu_source_to_targets in supported_upgrade_paths:
        # No need to use matches_version - our version list is always a singleton
        if ipu_source_to_targets.source_version == source_version:
            return True

    return False
