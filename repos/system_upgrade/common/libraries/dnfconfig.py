from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import get_leapp_packages
from leapp.libraries.stdlib import api, CalledProcessError


def _strip_split(data, sep, maxsplit=-1):
    """
    Just like str.split(), but remove ambient whitespaces from all items
    """
    return [item.strip() for item in data.split(sep, maxsplit)]


def _get_main_dump(context, disable_plugins):
    """
    Return the dnf configuration dump of main options for the given context.

    Returns the list of lines after the line with "[main]" section
    """

    cmd = ['dnf', 'config-manager', '--dump']

    if disable_plugins:
        for plugin in disable_plugins:
            cmd += ['--disableplugin', plugin]

    try:
        data = context.call(cmd, split=True)['stdout']
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


def _get_excluded_pkgs(context, disable_plugins):
    """
    Return the list of excluded packages for DNF in the given context.

    It shouldn't be used on the source system. It is expected this functions
    is called only in the target userspace container or on the target system.
    """
    pkgs = _strip_split(_get_main_dump(context, disable_plugins).get('exclude', ''), ',')
    return [i for i in pkgs if i]


def _set_excluded_pkgs(context, pkglist, disable_plugins):
    """
    Configure DNF to exclude packages in the given list

    Raise the CalledProcessError on error.
    """
    exclude = 'exclude={}'.format(','.join(pkglist))
    cmd = ['dnf', 'config-manager', '--save', '--setopt', exclude]

    if disable_plugins:
        for plugin in disable_plugins:
            cmd += ['--disableplugin', plugin]

    try:
        context.call(cmd)
    except CalledProcessError:
        api.current_logger().error('Cannot set the dnf configuration')
        raise
    api.current_logger().debug('The DNF configuration has been updated to exclude leapp packages.')


def exclude_leapp_rpms(context, disable_plugins):
    """
    Ensure the leapp RPMs are excluded from any DNF transaction.

    This has to be called several times to ensure that our RPMs are not removed
    or updated (replaced) during the IPU. The action should happen inside
        - the target userspace container
        - on the host system
    So user will have to drop these packages from the exclude after the
    upgrade.
    """
    to_exclude = list(set(_get_excluded_pkgs(context, disable_plugins) + get_leapp_packages()))
    _set_excluded_pkgs(context, to_exclude, disable_plugins)
