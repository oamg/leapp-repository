from leapp.actors import Actor
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag

from subprocess import check_call

class UpdateEtcSysconfigKernel(Actor):
    name = 'update_etc_sysconfig_kernel'
    description = 'Updates /etc/sysconfig/kernel DEFAULTKERNEL entry from kernel to kernel-core.'
    consumes = ()
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        check_call(['/bin/sed', '-i', 's/^DEFAULTKERNEL=kernel$/DEFAULTKERNEL=kernel-core/g', '/etc/sysconfig/kernel'])
