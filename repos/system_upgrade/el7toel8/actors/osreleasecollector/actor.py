from leapp.actors import Actor
from leapp.models import Inhibitor, OSReleaseFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class OSReleaseCollector(Actor):
    """
    Provides data about System OS release.

    After collecting data from /etc/os-release file, a message with relevant data will be produced.
    """

    name = 'os_release_collector'
    consumes = ()
    produces = (Inhibitor, OSReleaseFacts,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        os_data_file = '/etc/os-release'
        os_data = {}

        try:
            with open(os_data_file) as f:
                os_data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
        except IOError as e:
            self.produce(Inhibitor(
                summary='Error while collecting system OS facts',
                details=str(e),
                solutions=None
            ))
            return

        self.produce(OSReleaseFacts(
            id=os_data.get('ID', '').strip('"'),
            name=os_data.get('NAME', '').strip('"'),
            pretty_name=os_data.get('PRETTY_NAME', '').strip('"'),
            version=os_data.get('VERSION', '').strip('"'),
            version_id=os_data.get('VERSION_ID', '').strip('"'),
            variant=os_data.get('VARIANT', '').strip('"') or None,
            variant_id=os_data.get('VARIANT_ID', '').strip('"') or None
        ))
