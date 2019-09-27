import os

from leapp.actors import Actor
from leapp.libraries.common import mounting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ZiplConvertToBLSCFG(Actor):
    """
    This actor converts the zipl boot loader configuration to the the boot loader specification on s390x systems.
    """

    name = 'zipl_convert_to_blscfg'
    consumes = (TargetUserSpaceInfo,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        if architecture.matches_architecture(architecture.ARCH_S390X):
            userspace = next(self.consume(TargetUserSpaceInfo), None)
            if userspace:
                with mounting.BindMount(source='/boot', target=os.path.join(userspace.path, 'host-boot')):
                    userspace_zipl_conf = os.path.join(userspace.path, 'etc', 'zipl.conf')
                    if os.path.exists(userspace_zipl_conf):
                        os.remove(os.path.join(userspace.path, 'etc', 'zipl.conf'))
                    with mounting.NullMount(target=userspace.path) as userspace:
                        with userspace.spawn() as context:
                            context.copy_to('/etc/zipl.conf', '/etc/zipl.conf')
                            try:
                                context.call(
                                    ['/usr/sbin/zipl-switch-to-blscfg',
                                     '--bls-directory', '/host-boot/loader/entries'])
                                context.copy_from('/etc/zipl.conf', '/etc/zipl.conf')
                            except (OSError, CalledProcessError):
                                self.log.error(
                                    'Failed to execute zipl-switch-to-blscfg to convert to zipl configuration to BLS',
                                    exc_info=True
                                )
