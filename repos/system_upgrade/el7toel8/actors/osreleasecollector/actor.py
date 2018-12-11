from leapp.actors import Actor
from leapp.models import CheckResult, OSReleaseFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class OSReleaseCollector(Actor):
    name = 'os_release_collector'
    description = 'Actor collecting facts about system OS'
    consumes = ()
    produces = (CheckResult, OSReleaseFacts,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        os_data_file = '/etc/os-release'
        os_data = {}

        try:
            with open(os_data_file) as f:
                os_data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
        except IOError as e:
            self.produce(CheckResult(
                severity='Error',
                result='Fail',
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
