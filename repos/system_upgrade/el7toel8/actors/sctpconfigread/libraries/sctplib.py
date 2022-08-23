#
# Helper functions
#

from os.path import isfile

from leapp.libraries.actor import sctpdlm
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import ActiveKernelModulesFacts


def anyfile(files):
    """
    Determines if any of the given paths exist and are a file.

    :type files: tuple of str
    :return: True if any of the given paths exists and it is a file.
    :rtype: bool
    """
    for f in files:
        try:
            if isfile(f):
                return True
        except OSError:
            continue
    return False


def is_module_loaded(module):
    """
    Determines if the given kernel module has been reported in the ActiveKernelModuleFacts as loaded.

    :return: True if the module has been found in the ActiveKernelModuleFacts.
    :rtype: bool
    """
    for fact in api.consume(ActiveKernelModulesFacts):
        for active_module in fact.kernel_modules:
            if active_module.filename == module:
                return True
    return False


def is_sctp_used():
    """
    Logic function that decides whether SCTP is being used on this machine.

    :return: True if SCTP usage was detected.
    :rtype: bool
    """

    # If anything is using SCTP, be it for listening on new connections or
    # connecting somewhere else, the module will be loaded. Thus, no need to
    # also probe on sockets.
    if is_module_loaded('sctp'):
        return True

    # Basic files from lksctp-tools. This check is enough and checking RPM
    # database is an overkill here and this allows for checking for
    # manually installed ones, which is possible.
    lksctp_files = ['/usr/lib64/libsctp.so.1',
                    '/usr/lib/libsctp.so.1',
                    '/usr/bin/sctp_test']
    if anyfile(lksctp_files):
        api.current_logger().debug('At least one of lksctp files is present.')
        return True

    if sctpdlm.is_dlm_using_sctp():
        return True

    return False


def was_sctp_used():
    """
    Determines whether SCTP has been used in the path month, by checking the journalctl.

    :return: True if SCTP usage has been found.
    :rtype: bool
    """
    try:
        run(['check_syslog_for_sctp.sh'])
    except CalledProcessError:
        api.current_logger().debug('Nothing regarding SCTP was found on journal.')
        return False
    api.current_logger().debug('Found logs regarding SCTP on journal.')
    return True


def is_sctp_wanted():
    """
    Decision making function that decides based on the current or past usage of SCTP, the SCTP module is wanted
    on the new system.

    :return: True if SCTP seems to be in use or has been recently used.
    :rtype: bool
    """
    if is_sctp_used():
        api.current_logger().info('SCTP is being used.')
        return True

    if was_sctp_used():
        api.current_logger().info('SCTP was used.')
        return True

    api.current_logger().info('SCTP is not being used and neither wanted.')
    return False
