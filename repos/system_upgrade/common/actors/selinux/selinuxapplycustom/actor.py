import os
import shutil

from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor import selinuxapplycustom
from leapp.libraries.actor.selinuxapplycustom import BACKUP_DIRECTORY
from leapp.libraries.stdlib import CalledProcessError, run
from leapp.models import SELinuxCustom, SELinuxModules
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag

WORKING_DIRECTORY = '/tmp/selinux/'


class SELinuxApplyCustom(Actor):
    """
    Re-apply SELinux customizations from the original RHEL installation

    Re-apply SELinux policy customizations (custom policy modules and changes
    introduced by semanage). Any changes (due to incompatibility with
    SELinux policy in the upgraded system) are reported to user.
    """
    name = 'selinuxapplycustom'
    consumes = (SELinuxCustom, SELinuxModules)
    produces = (reporting.Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        # save progress for repoting purposes
        failed_modules = []
        failed_custom = []

        # clear working directory
        shutil.rmtree(WORKING_DIRECTORY, ignore_errors=True)

        try:
            os.mkdir(WORKING_DIRECTORY)
        except OSError:
            self.log.warning('Failed to create working directory! Aborting.')
            return

        # get list of policy modules after the upgrade
        installed_modules = set(
            [module[0] for module in selinuxapplycustom.list_selinux_modules()]
        )

        # import custom SElinux modules
        for semodules in self.consume(SELinuxModules):
            self.log.info(
                'Processing custom SELinux policy modules. Count: {}.'.format(len(semodules.modules))
            )
            # check for presence of udica templates and make sure to install their latest versions
            selinuxapplycustom.install_udica_templates(semodules.templates)

            if not semodules.modules:
                continue

            command = ['semodule']
            for module in semodules.modules:
                # Skip modules that are already installed. This prevents DSP modules installed with wrong
                # priority (usually 400) from being overwritten by an older version
                if module.name in installed_modules:
                    self.log.info(
                        'Skipping module {} on priority {} because it is already installed.'.format(
                            module.name,
                            module.priority
                        )
                    )
                    continue

                # cil module files need to be extracted to disk in order to be installed
                cil_filename = os.path.join(
                    WORKING_DIRECTORY, '{}.cil'.format(module.name)
                )
                self.log.info(
                    'Installing module {} on priority {}.'.format(module.name, module.priority)
                )
                if module.removed:
                    self.log.warning(
                        '{}: The following lines where removed because of incompatibility:\n{}'.format(
                            module.name,
                            '\n'.join(module.removed)
                        )
                    )
                # write module content to disk
                try:
                    with open(cil_filename, 'w') as cil_file:
                        cil_file.write(module.content)
                except OSError as e:
                    self.log.warning('Error writing {} : {}'.format(cil_filename, e))
                    continue

                command.extend(['-X', str(module.priority), '-i', cil_filename])

            try:
                run(command)
            except CalledProcessError as e:
                self.log.warning(
                    'Error installing modules in a single transaction:'
                    '{}\nRetrying -- now each module will be installed separately.'.format(e.stderr)
                )
                # Retry, but install each module separately
                for module in semodules.modules:
                    if module.name in installed_modules:
                        continue
                    cil_filename = os.path.join(
                        WORKING_DIRECTORY, '{}.cil'.format(module.name)
                    )
                    self.log.info(
                        'Installing module {} on priority {}.'.format(module.name, module.priority)
                    )
                    try:
                        run(['semodule',
                             '-X', str(module.priority),
                             '-i', cil_filename
                             ]
                            )
                    except CalledProcessError as e:
                        self.log.warning('Error installing module: {}'.format(e.stderr))
                        failed_modules.append(module.name)
                        selinuxapplycustom.back_up_failed(cil_filename)
                        continue

        # import SELinux customizations collected by "semanage export"
        for custom in self.consume(SELinuxCustom):
            self.log.info(
                'Importing the following SELinux customizations collected by "semanage export":\n{}'.format(
                    '\n'.join(custom.commands)
                )
            )
            # import customizations
            try:
                run(['semanage', 'import'], stdin='\n'.join(custom.commands))
            except CalledProcessError as e:
                self.log.warning(
                    'Error importing SELinux customizations in a single transaction:'
                    '{}\nRetrying -- now each command will be applied separately.'.format(e.stderr)
                )
                for cmd in custom.commands:
                    try:
                        run(['semanage', 'import'], stdin='{}\n'.format(cmd))
                    except CalledProcessError as e:
                        self.log.warning('Error applying "semanage {}": {}'.format(cmd, e.stderr))
                        failed_custom.append(cmd)
                continue

        # clean-up
        shutil.rmtree(WORKING_DIRECTORY, ignore_errors=True)

        if failed_modules or failed_custom:
            summary = ''
            if failed_modules:
                summary = (
                    'The following policy modules couldn\'t be installed: {}.\n'
                    'You can review their content in {}.'.format(
                        ', '.join(failed_modules), BACKUP_DIRECTORY
                    )
                )
            if failed_custom:
                if summary:
                    summary = '{}\n\n'.format(summary)
                summary = '{}The following commands couldn\'t be applied:\n{}'.format(
                    summary, '\n'.join(['semanage {}'.format(x) for x in failed_custom])
                )

            reporting.create_report(
                [
                    reporting.Title(
                        'SELinux failed to reapply some customizations after the upgrade.'
                    ),
                    reporting.Summary(summary),
                    reporting.Severity(reporting.Severity.MEDIUM),
                    reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.SELINUX]),
                ]
                + [
                    reporting.RelatedResource(
                        'file', os.path.join(BACKUP_DIRECTORY, '{}.cil'.format(x))
                    )
                    for x in failed_modules
                ]
            )
