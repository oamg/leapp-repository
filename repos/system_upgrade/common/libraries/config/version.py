import operator

import six

from leapp.libraries.stdlib import api

OP_MAP = {
    '>': operator.gt,
    '>=': operator.ge,
    '<': operator.lt,
    '<=': operator.le
}

_SUPPORTED_VERSIONS = {
    # Note: 'rhel-alt' is detected when on 'rhel' with kernel 4.x
    '7': {'rhel': ['7.9'], 'rhel-alt': [], 'rhel-saphana': ['7.9']},
    '8': {'rhel': ['8.6', '8.8'], 'rhel-saphana': ['8.6', '8.8']},
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


def _version_to_tuple(version):
    """Converts the version string ``major.minor`` to ``(major, minor)`` int tuple."""
    major, minor = version.split('.')
    return (int(major), int(minor))


def _validate_versions(versions):
    """Raise ``TypeError`` if provided versions are not strings in the form ``<integer>.<integer>``."""
    for ver in versions:
        split = ver.split('.')
        if not len(split) == 2 or not all(x.isdigit() for x in split):
            raise ValueError("Versions have to be in the form of '<integer>.<integer>' "
                             "but provided was '{}'".format(versions))


def _simple_versions(versions):
    """Return ``True`` if provided versions are list of strings without comparison operators."""
    return all(len(v.split()) == 1 for v in versions)


def _cmp_versions(versions):
    """Return ``True`` if provided versions are list of strings with comparison operators."""
    split = [v.split() for v in versions]
    if not all(len(s) == 2 for s in split):
        return False

    return all(s[0] in OP_MAP for s in split)


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
    _validate_versions([detected])

    if _simple_versions(match_list):
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
    return '.rt' in conf.kernel.split('-')[1]


def is_supported_version():
    """
    Verify if the current system version is supported for the upgrade.

    :return: `True` if the current version is supported and `False` otherwise.
    :rtype: bool
    """
    release_id, version_id = current_version()
    if is_rhel_alt():
        release_id = 'rhel-alt'
    elif is_sap_hana_flavour():
        release_id = 'rhel-saphana'

    if not matches_release(SUPPORTED_VERSIONS, release_id):
        return False

    return matches_version(SUPPORTED_VERSIONS[release_id], version_id)
