from leapp.actors import Actor
from leapp.libraries.stdlib import run
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag


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
        run(['/bin/sed',
             '-i',
             's/^DEFAULTKERNEL=kernel$/DEFAULTKERNEL=kernel-core/g',
             '/etc/sysconfig/kernel'])
