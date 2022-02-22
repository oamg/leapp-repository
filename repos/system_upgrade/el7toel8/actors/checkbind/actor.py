from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor import iscmodel
from leapp.libraries.stdlib import api
from leapp.models import BindFacts, InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBind(Actor):
    """Actor parsing BIND configuration and checking for known issues in it."""

    name = 'check_bind'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (BindFacts, reporting.Report)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    pkg_names = {'bind', 'bind-sdb', 'bind-pkcs11'}

    def has_package(self, t_rpms):
        """Replacement for broken leapp.libraries.common.rpms.has_package."""
        for fact in self.consume(t_rpms):
            for rpm in fact.items:
                if rpm.name in self.pkg_names:
                    return True
        return False

    def process(self):
        if not self.has_package(InstalledRedHatSignedRPM):
            self.log.debug('bind is not installed')
            return

        facts = iscmodel.get_facts('/etc/named.conf')
        report = iscmodel.make_report(facts)

        if report:
            api.produce(facts)
            self.log.info('BIND configuration issues were found.')
            reporting.create_report(report)
        else:
            self.log.debug('BIND configuration seems compatible.')
