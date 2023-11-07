#!/usr/libexec/platform-python

from os import listdir, readlink
from os.path import islink
from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import ActiveKernelModulesFacts

iodevs = ['/dev/mptctl', '/dev/mpt2ctl', '/dev/mpt3ctl']


def get_open_files():
    """
    Mimics fuser to get the filenames corresponding to
    open file descriptors for running processes
    """
    open_files = {}
    for pid in listdir('/proc'):
        if not pid.isdigit():
            continue
        open_list = []
        for fd in listdir('/proc/%s/fd' % pid):
            fd_path = '/proc/%s/fd/%s' % (pid, fd)
            if islink(fd_path):
                open_list.append(readlink(fd_path))
        if len(open_list):
            open_files[pid] = open_list
    return open_files


def get_process_info(pid):
    """ Return the PID alongside the command line in use """
    try:
        with open('/proc/%s/cmdline' % pid, 'r') as f:
            cmdline = f.read().split('\0')
        return "%s: %s" % (pid, " ".join(cmdline))
    except IOError: # in case the process is already dead
        return


def get_mptctl_locks(open_files):
    """
    Get the list of processes that prevent the unloading of the mptctl module
    Note: monitoring tools from Dell and HP are known to use it.
    """
    locks = []
    for pid in open_files.keys():
        if any(f in iodevs for f in open_files[pid]):
            locks.append(pid)
    return locks


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


def check_mptctl():
    """ Main actor process """
    if not is_module_loaded("mptctl"):
        return

    mptctl_locks = get_mptctl_locks(get_open_files())

    if not mptctl_locks:
        return

    processes = '\n'.join([get_process_info(pid) for pid in mptctl_locks])

    summary = (
        'Leapp detected that the following processes are using the mptctl '
        'kernel module which will be removed in RHEL 8:\n{0}'
    )

    hint = (
        'Stop this application or the service that runs this process.'
    )

    reporting.create_report([
        reporting.Title(
            'Detected processes that are using mptctl.'
        ),
        reporting.Summary(summary.format(processes)),
        reporting.Remediation(hint=hint.format(processes)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])

