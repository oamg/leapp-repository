from leapp.actors import Actor
from leapp.libraries.actor.library import migrate_ntp
from leapp.models import Report, NtpMigrationDecision
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateNtp(Actor):
    name = 'migrate_ntp'
    description = 'Migrate ntp and/or ntpdate configuration to chrony.'
    consumes = (NtpMigrationDecision,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(NtpMigrationDecision):
            migrate_ntp(decision.migrate_services, decision.config_tgz64)
