from leapp.actors import Actor
from leapp.libraries.actor.migratentp import migrate_ntp
from leapp.models import NtpMigrationDecision, Report
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateNtp(Actor):
    """
    Migrate ntp and/or ntpdate configuration to chrony.
    """

    name = 'migrate_ntp'
    consumes = (NtpMigrationDecision,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(NtpMigrationDecision):
            migrate_ntp(decision.migrate_services, decision.config_tgz64)
