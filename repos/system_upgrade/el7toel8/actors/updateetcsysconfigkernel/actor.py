from leapp.actors import Actor
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag

from subprocess import check_call

class UpdateEtcSysconfigKernel(Actor):
    """
    Update /etc/sysconfig/kernel file.

    In order to proceed with Upgrade process, DEFAULTKERNEL entry should be updated from kernel to
    kernel-core.
    """

    name = 'update_etc_sysconfig_kernel'
    consumes = ()
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        check_call(['/bin/sed', '-i', 's/^DEFAULTKERNEL=kernel$/DEFAULTKERNEL=kernel-core/g', '/etc/sysconfig/kernel'])
