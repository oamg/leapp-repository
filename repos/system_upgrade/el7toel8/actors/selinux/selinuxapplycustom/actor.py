from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxCustom, CheckResult
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import call
import subprocess
import os
from shutil import rmtree

WORKING_DIRECTORY = '/tmp/selinux/'

class SELinuxApplyCustom(Actor):
    name = 'selinuxapplycustom'
    description = 'No description has been provided for the selinuxapplycustom actor.'
    consumes = (SELinuxCustom, SELinuxModules, )
    produces = (CheckResult, )
    tags = (ApplicationsPhaseTag, IPUWorkflowTag, )

    def process(self):
        # cil module files need to be extracted to disk in order to be installed
        try:
            # clear working directory
            rmtree(WORKING_DIRECTORY)
        except OSError:
            #expected
            pass
        try:
            os.mkdir(WORKING_DIRECTORY)
        except OSError:
            self.log.info("Failed to access working directory! Aborting.")
            return

        # import custom SElinux modules
        for semodules in self.consume(SELinuxModules):
            self.log.info("Processing custom SELinux policy modules. Count: " +
                str(len(semodules.modules))
            )
            for module in semodules.modules:
                cil_filename = WORKING_DIRECTORY + module.name + ".cil"
                self.log.info("Installing " + module.name
                 + " on priority " + str(module.priority) + ".")
                if module.removed:
                    self.log.info("The following lines where removed because of incompatibility: ")
                    self.log.info('\n'.join(module.removed))
                # write module content to disk
                try:
                    with open(cil_filename, 'w') as file:
                        file.write(module.content)
                except OSError as e:
                    self.log.info("Error writing " + cil_filename + " :" + e.strerror)
                    continue

                try:
                    semanage = call([
                        'semodule',
                        '-X',
                        str(module.priority),
                        '-i',
                        cil_filename]
                    )
                except subprocess.CalledProcessError as e:
                    self.log.info("Error installing module: " + e.strerror)
                    pass
                try:
                    os.remove(cil_filename)
                except OSError:
                    self.log.info("Error removing module file")
        # import SELinux customizations collected by "semanage export"
        for custom in self.consume(SELinuxCustom):
            self.log.info('Importing SELinux customizations collected by "semanage export".')
            semanage_filename = WORKING_DIRECTORY + "semanage"
            # save SELinux customizations to disk
            try:
                with open(semanage_filename, 'w') as file:
                    file.write('\n'.join(custom.commands))
            except OSError as e:
                self.log.info("Error writing SELinux customizations:" + e.strerror)
            # import customizations
            try:
                call(['semanage', 'import', '-f', semanage_filename])
            except subprocess.CalledProcessError:
                continue
            # clean-up
            try:
                os.remove(semanage_filename)
            except OSError:
                continue

        # clean-up
        try:
            os.rmdir("/tmp/selinux")
        except OSError:
            pass

        self.log.info("SElinux customizations reapplied successfully.")
        self.produce(
           CheckResult(
               severity='Info',
               result='Pass',
               summary='SElinux customizations reapplied successfully.',
               details='SELinux modules with non-standard priority and other custom settings where reapplied after the upgrade.',
               solutions=None
        ))


