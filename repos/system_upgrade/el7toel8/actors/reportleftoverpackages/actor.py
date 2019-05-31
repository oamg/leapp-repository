from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic
from leapp.models import LeftoverPackages, RemovedPackages
from leapp.reporting import Report
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag


class ReportLeftoverPackages(Actor):
    """
    Collect messages about leftover el7 packages and generate report for users.

    Depending on execution of previous actors, generated report contains information that there are still el7 packages
    present on the system, which makes it unsupported or lists packages that have been removed.
    """

    name = 'report_leftover_packages'
    consumes = (LeftoverPackages, RemovedPackages)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        removed_packages = next(self.consume(RemovedPackages), None)
        leftover_packages = next(self.consume(LeftoverPackages), LeftoverPackages())
        to_remove = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in leftover_packages.items]

        if removed_packages:
            title = 'Leftover RHEL 7 packages have been removed'

            if removed_packages.items:
                removed = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in removed_packages.items]
                report_generic(summary='Following packages have been removed:\n{}'.format('\n'.join(removed)),
                               title=title)
            else:
                summary = ('Following packages have been removed:\n'
                           '{}\n'
                           'Dependent packages may have been removed as well, please check that you are not missing '
                           'any packages.\n'.format('\n'.join(to_remove)))
                report_generic(title=title, summary=summary, severity='high')
            return

        if not leftover_packages.items:
            self.log.info('No leftover packages, skipping...')
            return

        summary = 'Following RHEL 7 packages have not been upgraded:\n{}\n'.format('\n'.join(to_remove))
        summary += 'Please remove these packages to keep your system in supported state.\n'
        report_generic(title='Some RHEL 7 packages have not been upgraded',
                       summary=summary,
                       severity='high')
