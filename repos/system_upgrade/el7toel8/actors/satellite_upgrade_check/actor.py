from leapp.actors import Actor
from leapp.libraries.actor.satellite_upgrade_check import satellite_upgrade_check
from leapp.models import Report, SatelliteFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SatelliteUpgradeCheck(Actor):
    """
    Check state of Satellite system before upgrade
    """

    name = 'satellite_upgrade_check'
    consumes = (SatelliteFacts,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        facts = next(self.consume(SatelliteFacts), None)
        if not facts or not facts.has_foreman:
            return

        satellite_upgrade_check(facts)
