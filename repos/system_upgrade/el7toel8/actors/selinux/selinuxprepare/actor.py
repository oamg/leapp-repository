from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxCustom
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import run, CalledProcessError

class SELinuxPrepare(Actor):
    '''
    Remove selinux policy customizations before updating selinux-policy* packages

    RHEL-7 policy customizations could cause policy package upgrade to fail and therefore
    need to be removed. Customizations introduced by semanage are removed first,
    followed by custom policy modules gathered by SELinuxContentScanner.
    '''

    name = 'selinuxprepare'
    # TODO change description to doc string - first line is summary, followed by more in-depth description
    consumes = (SELinuxCustom, SELinuxModules)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        # remove SELinux customizations done by semanage -- to be reintroduced after the upgrade
        self.log.info('Removing SELinux customizations introduced by semanage.')

        semanage_options = ["login","user","port","interface","module","node","fcontext","boolean","ibpkey","ibendport"]
        # permissive domains are handled by porting modules (permissive -a adds new cil module with priority 400)
        for option in semanage_options:
            try:
                run(['semanage', option, '-D'])
            except CalledProcessError:
                continue

        # remove custom SElinux modules - to be reinstalled after the upgrade
        for semodules in self.consume(SELinuxModules):
            self.log.info("Removing custom SELinux policy modules. Count: %d", len(semodules.modules))
            for module in semodules.modules:
                self.log.info("Removing %s on priority %d.", module.name, module.priority)
                try:
                    run([
                        'semodule',
                        '-X',
                        str(module.priority),
                        '-r',
                        module.name]
                    )
                except CalledProcessError as e:
                    self.log.info("Failed to remove module %s on priority %d: %s", module.name, module.priority, str(e))
                    continue

        self.log.info("SElinux customizations removed successfully.")
