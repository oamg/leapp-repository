from leapp.actors import Actor
from leapp.reporting import create_report
from leapp import reporting
from leapp.libraries.stdlib import config
from leapp.models import Report, SkippedRepositories
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSkippedRepositories(Actor):
    """
    Produces a report if any repositories enabled on the system are going to be skipped.

    The report produced by this actor should additionally include any package that is affected due to skipping
    the repository.
    """

    name = 'check_skipped_repositories'
    consumes = (SkippedRepositories,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        repos = set()
        packages = set()

        for message in self.consume(SkippedRepositories):
            repos.update(message.repos)
            packages.update(message.packages)

        if repos:
            title = 'Some enabled RPM repositories are unknown to Leapp'
            summary_data = []
            summary_data.append('The following repositories with Red Hat-signed packages are unknown to Leapp:')
            summary_data.extend(['- {}'.format(r) for r in repos])
            summary_data.append('And the following packages installed from those repositories may not be upgraded:')
            summary_data.extend(['- {}'.format(p) for p in packages])
            summary = '\n'.join(summary_data)

            packages_related = [reporting.RelatedResource('package', str(p)) for p in packages]
            repos_related = [reporting.RelatedResource('repository', str(r)) for r in repos]

            create_report([
                reporting.Title(title),
                reporting.Summary(summary),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.REPOSITORY]),
                reporting.Remediation(
                    hint='You can file a request to add this repository to the scope of in-place upgrades '
                         'by filing a support ticket')
            ] + packages_related + repos_related)

            if config.is_verbose():
                self.log.info('\n'.join([title, summary]))
