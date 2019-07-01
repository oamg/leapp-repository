import six

from leapp.libraries.stdlib import api


ARCH_X86_64 = 'x86_64'
ARCH_ARM64 = 'aarch64'
ARCH_PPC64LE = 'ppc64le'
ARCH_S390X = 's390x'
ARCH_ACCEPTED = (ARCH_X86_64, ARCH_ARM64, ARCH_PPC64LE, ARCH_S390X)


def matches_architecture(match_list):
    """
    Check if one of provided architectures matches the system's one.

    :param match: architectures to check against
    :type match: list, tuple of strings
    :return: ``True`` if system's architecture matches one of the values in match_list, ``False`` otherwise
    :rtype: bool
    """
    if not isinstance(match_list, (list, tuple)):
        raise TypeError("Architectures to check against have to be a list or tuple "
                        "but provided was {}: '{}'".format(type(match_list), match_list))
    if not all(isinstance(e, six.string_types) for e in match_list):
        raise TypeError("Architectures to check against have to be a list or tuple of strings "
                        "but provided was {}: '{}'".format([type(e) for e in match_list], match_list))
    unsupported = set(match_list).difference(ARCH_ACCEPTED)
    if unsupported:
        api.current_logger().warn("Unsupported architecture specified: {}".format(unsupported))
    return api.current_actor().configuration.architecture in match_list
