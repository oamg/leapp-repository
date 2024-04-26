import glob
import os

from leapp.actors import Actor
from leapp.models import SatelliteFacts, SystemdServicesTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

SYSTEMD_WANTS_BASE = '/etc/systemd/system/multi-user.target.wants/'
SERVICES_TO_DISABLE = ['dynflow-sidekiq@*', 'foreman', 'foreman-proxy',
                       'httpd', 'postgresql', 'pulpcore-api', 'pulpcore-content',
                       'pulpcore-worker@*', 'tomcat', 'redis']


class SatelliteUpgradeServices(Actor):
    """
    Reconfigure Satellite services
    """

    name = 'satellite_upgrade_services'
    consumes = (SatelliteFacts,)
    produces = (SystemdServicesTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        facts = next(self.consume(SatelliteFacts), None)
        if not facts or not facts.has_foreman:
            return

        # disable services, will be re-enabled by the installer
        services_to_disable = []
        for service_name in SERVICES_TO_DISABLE:
            for service in glob.glob(os.path.join(SYSTEMD_WANTS_BASE, '{}.service'.format(service_name))):
                services_to_disable.append(os.path.basename(service))
        self.produce(SystemdServicesTasks(to_disable=services_to_disable))
