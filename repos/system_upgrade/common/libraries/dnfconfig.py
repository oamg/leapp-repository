from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api, CalledProcessError


def get_leapp_packages():
    """
    Return the list of leapp and leapp-repository rpms that should be preserved
    during the upgrade.

    It's list of packages that should be preserved, not what is really
    installed.

    The snactor RPM doesn't have to be installed, but if so, we have to take
    care about that too as well to preven broken dnf transaction.
    """
    # TODO: should we set the seatbelt and exclude leapp RPMs from the target
    # system too?
    generic = ['leapp', 'snactor']
    if get_source_major_version() == '7':
        return generic + ['python2-leapp', 'leapp-upgrade-el7toel8']

    return generic + ['python3-leapp', 'leapp-upgrade-el8toel9']


def _strip_split(data, sep, maxsplit=-1):
    """
    Just like str.split(), but remove ambient whitespaces from all items
    """
    return [item.strip() for item in data.split(sep, maxsplit)]


def _get_main_dump(context):
    """
    Return the dnf configuration dump of main options for the given context.

    Returns the list of lines after the line with "[main]" section
    """

    try:
        data = context.call(['dnf', 'config-manager', '--dump'], split=True)['stdout']
    except CalledProcessError as e:
        api.current_logger().error('Cannot obtain the dnf configuration')
        raise StopActorExecutionError(
            message='Cannot obtain data about the DNF configuration',
            details={'stdout': e.stdout, 'stderr': e.stderr}
        )

    try:
        # return index of the first item in the main section
        main_start = data.index('[main]') + 1
    except ValueError:
        raise StopActorExecutionError(
            message='Invalid DNF configuration data (missing [main])',
            details=data,
        )

    output_data = {}
    for line in data[main_start:]:
        try:
            key, val = _strip_split(line, '=', 1)
        except ValueError:
            # This is not expected to happen, but call it a seatbelt in case
            # the dnf dump implementation will change and we will miss it
            # This is not such a hard error as the one above, as it means
            # some values could be incomplete, however we are still able
            # to continue.
            api.current_logger().warning(
                'Cannot parse the dnf dump correctly, line: {}'.format(line))
            pass
        output_data[key] = val

    return output_data


def _get_excluded_pkgs(context):
    """
    Return the list of excluded packages for DNF in the given context.

    It shouldn't be used on the source system. It is expected this functions
    is called only in the target userspace container or on the target system.
    """
    pkgs = _strip_split(_get_main_dump(context).get('exclude', ''), ',')
    return [i for i in pkgs if i]


def _set_excluded_pkgs(context, pkglist):
    """
    Configure DNF to exclude packages in the given list

    Raise the CalledProcessError on error.
    """
    exclude = 'exclude={}'.format(','.join(pkglist))
    cmd = ['dnf', 'config-manager', '--save', '--setopt', exclude]

    try:
        context.call(cmd)
    except CalledProcessError:
        api.current_logger().error('Cannot set the dnf configuration')
        raise
    api.current_logger().debug('The DNF configuration has been updated to exclude leapp packages.')


def exclude_leapp_rpms(context):
    """
    Ensure the leapp RPMs are excluded from any DNF transaction.

    This has to be called several times to ensure that our RPMs are not removed
    or updated (replaced) during the IPU. The action should happen inside
        - the target userspace container
        - on the host system
    So user will have to drop these packages from the exclude after the
    upgrade.
    """
    to_exclude = list(set(_get_excluded_pkgs(context) + get_leapp_packages()))
    _set_excluded_pkgs(context, to_exclude)
