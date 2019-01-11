import json

from leapp.actors import Actor
from leapp.models import RpmTransactionTasks, InstalledRedHatSignedRPM
from leapp.tags import IPUWorkflowTag, FactsPhaseTag, ExperimentalTag


EVENTS = ('Present', 'Removed', 'Deprecated', 'Replaced', 'Split', 'Merged', 'Moved', 'Renamed')


class PesEventsScanner(Actor):
    name = 'pes_events_scanner'
    description = 'Retrieve all events provided by Package Evolution Service API'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    @staticmethod
    def get_packages(event, name):
        packages = (event.get(name, {}) or {}).get('package')
        if packages:
            return [p['name'] for p in packages if p]
        return []

    def process(self):
        installed_pkgs = set()
        for rpm_pkgs in self.consume(InstalledRedHatSignedRPM):
            installed_pkgs.update([pkg.name for pkg in rpm_pkgs.items])

        to_install = set()
        to_remove = set()

        with open(self.get_file_path('pes-events.json')) as f:
            data = json.load(f)['packageinfo']
            for event in data:
                action = EVENTS[event['action']]
                in_packages = self.get_packages(event, 'in_packageset')
                out_packages = self.get_packages(event, 'out_packageset')
                if not installed_pkgs.intersection(in_packages):
                    continue
                if action not in ('Present', 'Deprecated', 'Moved') and in_packages:
                    to_remove.update(in_packages)
                if out_packages:
                    to_install.update(out_packages)

        common = to_install.intersection(to_remove)
        to_install.difference_update(common)
        to_remove.difference_update(common)

        if to_install or to_remove:
            self.produce(RpmTransactionTasks(to_install=list(to_install), to_remove=list(to_remove)))

