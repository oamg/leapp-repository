from leapp.libraries.common.config.version import is_rhel_realtime
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InstalledTargetKernelVersion


def _get_kernel_version(kernel_name):
    try:
        kernels = run(['rpm', '-q', kernel_name], split=True)['stdout']
    except CalledProcessError:
        return ''

    target_major_version = api.current_actor().configuration.version.target.split('.')[0]

    for kernel in kernels:
        # name-version-release - we want the last two fields only
        version = '-'.join(kernel.split('-')[-2:])
        if 'el{}'.format(target_major_version) in version:
            return version
    return ''


def process():
    # pylint: disable=no-else-return  - false positive
    # TODO: should we take care about stuff of kernel-rt and kernel in the same
    # time when both are present? or just one? currently, handle only one
    # of these during the upgrade. kernel-rt has higher prio when original sys
    # was realtime

    if is_rhel_realtime():
        version = _get_kernel_version('kernel-rt')
        if version:
            api.produce(InstalledTargetKernelVersion(version=version))
            return
        else:
            api.current_logger().warning(
                'The kernel-rt rpm from the target RHEL has not been detected. '
                'Switching to non-preemptive kernel.'
            )
            # TODO: create report with instructions to install kernel-rt manually
            # - attach link to article if any
            # - this possibly happens just in case the repository with kernel-rt
            # # is not enabled during the upgrade.

    # standard (non-preemptive) kernel
    version = _get_kernel_version('kernel')
    if version:
        api.produce(InstalledTargetKernelVersion(version=version))
    else:
        # This is very unexpected situation. At least one kernel has to be
        # installed always. Some actors consuming the InstalledTargetKernelVersion
        # will crash without the created message. I am keeping kind of original
        # behaviour in this case, but at least the let me log the error msg
        #
        api.current_logger().error('Cannot detect any kernel RPM')
        # StopActorExecutionError('Cannot detect any target RHEL kernel RPM.')
