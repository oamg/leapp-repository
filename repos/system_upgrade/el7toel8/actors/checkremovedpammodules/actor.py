from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, PamConfiguration
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.reporting import create_report
from leapp import reporting


class CheckRemovedPamModules(Actor):
    """
    Check for modules that are not available in RHEL 8 anymore

    At this moment, we check only for pam_tally2. Few more modules
    are alredy covered in RemoveOldPAMModulesApply actor
    """

    name = 'removed_pam_modules'
    consumes = (PamConfiguration, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag, )

    def process(self):
        messages = self.consume(PamConfiguration)
        config = next(messages, None)
        if list(messages):
            api.current_logger().warning('Unexpectedly received more than one PamConfiguration message.')
        if not config:
            raise StopActorExecutionError(
                'Could not check pam configuration', details={'details': 'No PamConfiguration facts found.'}
            )

        # This list contain tupples of removed modules and their recommended replacements
        removed_modules = [
            ('pam_tally2', 'pam_faillock'),
            ]
        found_services = set()
        found_modules = set()
        replacements = set()
        for service in config.services:
            for module in removed_modules:
                removed = module[0]
                replacement = module[1]
                if removed in service.modules:
                    found_services.add(service.service)
                    found_modules.add(removed)
                    replacements.add(replacement)

        if found_modules:
            create_report([
                reporting.Title('The {} pam module(s) no longer available'.format(', '.join(found_modules))),
                reporting.Summary('The services {} using PAM are configured to '
                                  'use {} module(s), which is no longer available '
                                  'in Red Hat Enterprise Linux 8.'.format(
                                      ', '.join(found_services), ', '.join(found_modules))),
                reporting.Remediation(
                    hint='If you depend on its functionality, it is '
                         'recommended to migrate to {}. Otherwise '
                         'please remove the pam module(s) from all the files '
                         'under /etc/pam.d/.'.format(', '.join(replacements))
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.INHIBITOR]),
            ] + [reporting.RelatedResource('pam', r) for r in replacements | found_modules])
