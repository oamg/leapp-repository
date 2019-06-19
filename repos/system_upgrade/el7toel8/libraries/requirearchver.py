import operator
import platform

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api


def get_os_release_info(path):
    """
    Retrieve data about System OS release from provided file.

    :rtype: dictionary or None
    """
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
            return {key: value.strip('"') for key, value in data.items()}
    except IOError as e:
        reporting.report_generic(
            title='Error while collecting system OS facts',
            summary=str(e),
            severity='high',
            flags=['inhibitor'])
        return None


def _log_and_raise(reason, required, detected):
    """Log that requirements were not met and stop actor's execution by raising a StopActorExecution exception."""
    msg = 'Actor skipped, {reason} requirement not met, required: {required}, detected: {detected}'.format(
        reason=reason, required=required, detected=detected)
    api.current_logger().info(msg)
    raise StopActorExecution


def _log_passed(reason, required, detected):
    """Log that requirements were fulfilled."""
    msg = 'Requirement for {reason} fulfilled, required: {required}, detected: {detected}'.format(
        reason=reason, required=required, detected=detected)
    api.current_logger().debug(msg)


def require_arch(required):
    """
    Stop actor's execution if requirement on architecture is not met.

    :param required: list or tuple of vrchitectures
    :type required: list, tuple
    """
    if not isinstance(required, (list, tuple)):
        raise TypeError('Required architectures has to be a list or tuple: {}'.format(required))

    accepted = set(('ppc64le', 's390x', 'aarch64', 'x86_64'))
    unsupported = set(required).difference(accepted)
    if unsupported:
        api.current_logger().warn('Unsupported architecture specified: {}'.format(unsupported))

    detected = platform.machine()
    reason = 'architecture'
    if detected not in required:
        _log_and_raise(reason, required, detected)

    _log_passed(reason, required, detected)


def _require_minor_version(destination, required, detected):
    """
    Stop actor's execution if requirement on minor version is not met.

    :param destination: 'source' or 'target'
    :type destination: string
    :param required: list or tuple of versions - integers or strings in the form '<integer>['+'|'>'|'-'|'<']'
    :type required: list, tuple
    :param detected: Detected version
    :type detected: int
    """

    reason = "{}'s minor version".format(destination)

    if not isinstance(required, (list, tuple)):
        raise TypeError("Required {reason} has to be a list or tuple: {required}".format(
            reason=reason, required=required))

    if all(isinstance(r, int) for r in required):
        # required is list of versions
        if detected not in required:
            _log_and_raise(reason, required, detected)
    else:
        # required should be list of '<integer>['+'|'>','-','<']' strings
        fun_map = {'+': operator.gt, '>': operator.gt, '-': operator.lt, '<': operator.lt}
        try:
            if not all(fun_map[r[-1]](detected, int(r[:-1])) for r in required):
                _log_and_raise(reason, required, detected)
        except (KeyError, ValueError, TypeError):
            raise TypeError("Required {reason} has to be a list or tuple of integers or strings in the "
                            "form '<integer>['+'|'>'|'-'|'<']': {required}".format(
                                reason=reason, required=required))

    _log_passed(reason, required, detected)


# TODO: target's minor version will be specified using dynamic configuration phase, see #505 (add tests afterward)
# def require_tgt_minor_version(required):
#     """
#     Stop actor's execution if requirement on minor version of target system is not met.
#
#     :param destination: 'source' or 'target'
#     :type destination: string
#     :param required: list or tuple of versions - integers or strings in the form '<integer>['+'|'>'|'-'|'<']'
#     :type required: list, tuple
#     :param detected: Detected version
#     :type detected: int
#     """
#     detected = 0
#     _require_minor_version('target', required, detected)


def require_src_minor_version(required):
    """
    Stop actor's execution if requirement on minor version of source system is not met.

    :param destination: 'source' or 'target'
    :type destination: string
    :param required: list or tuple of versions - integers or strings in the form '<integer>['+'|'>'|'-'|'<']'
    :type required: list, tuple
    :param detected: Detected version
    :type detected: int
    """
    detected = int(get_os_release_info('/etc/os-release')['VERSION_ID'].split('.')[1])
    _require_minor_version('source', required, detected)
