import filecmp
import os

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ZiplConvertToBLSCFG(Actor):
    """
    Convert the zipl boot loader configuration to the the boot loader specification on s390x systems.
    """

    name = 'zipl_convert_to_blscfg'
    consumes = (TargetUserSpaceInfo,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_S390X):
            return
        userspace = next(self.consume(TargetUserSpaceInfo), None)
        if not userspace:
            # actually this should not happen, but in such case, we want to still
            # rather continue even if we boot into the old kernel, but in such
            # case, people will have to do manual actions.
            # NOTE: it is really just hypothetical
            self.log_error(
                'TargetUserSpaceInfo is missing. Cannot execute zipl-switch-to-blscfg'
                ' to convert the zipl configuration to BLS.'
            )
            raise StopActorExecutionError('GENERAL FAILURE: Input data for the actor are missing.')

        # replace the original boot directory inside the container by the host one
        # - as we cannot use zipl* pointing anywhere else than default directory
        # - no, --bls-directory is not solution
        with mounting.BindMount(source='/boot', target=os.path.join(userspace.path, 'boot')):
            userspace_zipl_conf = os.path.join(userspace.path, 'etc', 'zipl.conf')
            if os.path.exists(userspace_zipl_conf):
                os.remove(userspace_zipl_conf)
            with mounting.NullMount(target=userspace.path) as userspace:
                with userspace.nspawn() as context:
                    context.copy_to('/etc/zipl.conf', '/etc/zipl.conf')
                    # zipl needs this one as well
                    context.copy_to('/etc/machine-id', '/etc/machine-id')
                    try:
                        context.call(['/usr/sbin/zipl-switch-to-blscfg'])
                        if filecmp.cmp('/etc/zipl.conf', userspace_zipl_conf):
                            # When the files are same, zipl failed - see the switch script
                            raise OSError('Failed to convert the ZIPL configuration to BLS.')
                        context.copy_from('/etc/zipl.conf', '/etc/zipl.conf')
                    except OSError as e:
                        self.log.error('Could not call zipl-switch-to-blscfg command.',
                                       exc_info=True)
                        raise StopActorExecutionError(
                            message='Failed to execute zipl-switch-to-blscfg.',
                            details={'details': str(e)}
                        )
                    except CalledProcessError as e:
                        self.log.error('zipl-switch-to-blscfg execution failed,',
                                       exc_info=True)
                        raise StopActorExecutionError(
                            message='zipl-switch-to-blscfg execution failed with non zero exit code.',
                            details={'details': str(e), 'stdout': e.stdout, 'stderr': e.stderr}
                        )

                        # FIXME: we do not want to continue anymore, but we should clean
                        # better.
                        # NOTE: Basically, just removal of the /boot/loader dir content inside
                        # could be enough, but we cannot remove /boot/loader because of boom
                        # - - if we remove it, we will remove the snapshot as well
                        # - - on the other hand, we should't keep it there if zipl
                        # - - has not been converted to BLS
