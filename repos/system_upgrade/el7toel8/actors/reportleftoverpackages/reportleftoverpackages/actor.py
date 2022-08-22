from leapp.actors import Actor
from leapp.models import LeftoverPackages, RemovedPackages
from leapp.reporting import Report, create_report
from leapp import reporting
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
                create_report([
                    reporting.Title(title),
                    reporting.Summary('Following packages have been removed:\n{}'.format('\n'.join(removed))),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SANITY]),
                ] + [reporting.RelatedResource('package', pkg.name) for pkg in removed_packages.items])
            else:
                summary = ('Following packages have been removed:\n'
                           '{}\n'
                           'Dependent packages may have been removed as well, please check that you are not missing '
                           'any packages.\n'.format('\n'.join(to_remove)))

                create_report([
                    reporting.Title(title),
                    reporting.Summary(summary),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SANITY]),
                ] + [reporting.RelatedResource('package', pkg.name) for pkg in leftover_packages.items])
            return

        if not leftover_packages.items:
            self.log.info('No leftover packages, skipping...')
            return

        summary = 'Following RHEL 7 packages have not been upgraded:\n{}\n'.format('\n'.join(to_remove))
        summary += 'Please remove these packages to keep your system in supported state.\n'
        create_report([
            reporting.Title('Some RHEL 7 packages have not been upgraded'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
        ] + [reporting.RelatedResource('package', pkg.name) for pkg in leftover_packages.items])
