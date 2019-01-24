from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxCustom, CheckResult
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import call
import subprocess

class SELinuxPrepare(Actor):
    name = 'selinuxprepare'
    description = 'No description has been provided for the selinuxprepare actor.'
    consumes = (SELinuxCustom, SELinuxModules, )
    produces = (CheckResult, )
    tags = (PreparationPhaseTag, IPUWorkflowTag, )

    def process(self):
        # remove custom SElinux modules - to be reinstalled after the upgrade
        for semodules in self.consume(SELinuxModules):
            self.log.info("Removing custom SELinux policy modules. Count: " +
                str(len(semodules.modules))
            )
            for module in semodules.modules:
                self.log.info("Removing " + module.name
                 + " on priority " + str(module.priority) + ".")

                try:
                    semanage = call([
                        'semodule',
                        '-X',
                        str(module.priority),
                        '-r',
                        module.name]
                    )
                except subprocess.CalledProcessError:
                    self.log.info("Failed to remove " + module.name
                        + " on priority " + str(module.priority) + ".")
                    continue

        # remove SELinux customizations done by semanage -- to be reintroduced after the upgrade
        self.log.info('Removing SELinux customizations introduced by semanage.')

        semanage_options = ["login","user","port","interface","module","node","fcontext","boolean","permissive","dontaudit","ibpkey","ibendport"]
        for option in semanage_options:
            try:
                call(['semanage', option, '-D'])
            except subprocess.CalledProcessError:
                continue

        self.log.info("SElinux customizations removed successfully.")


