from leapp.actors import Actor
from leapp.libraries.common.modularity import get_modules
from leapp.libraries.stdlib import run
from leapp.models import InstalledRPMModuleMapping
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class MapInstalledRPMsToModules(Actor):
    """
    Map installed modular RPMS to the module streams they come from.
    """

    name = 'map_installed_rpms_to_modules'
    consumes = ()
    produces = (InstalledRPMModuleMapping,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        modules = get_modules()
        # empty on RHEL 7 - do not produce anything
        if not modules:
            return
        # assuming there's "module" in release of each modular RPM
        rpms = run(['rpm', '-qa', 'release=*module*'], split=True)['stdout']
        # create a reverse mapping from the RPMS to module streams
        rpm_streams = {}
        for module in modules:
            if 'artifacts' not in module['data']:
                continue
            for rpm in module['data']['artifacts']['rpms']:
                # we drop the epoch number first
                rpm_ne, rpm_vra = rpm.split(':', 1)
                rpm_n = rpm_ne.rsplit('-', 1)[0]
                rpm = '-'.join((rpm_n, rpm_vra))
                # stream could be int or float, convert it to str just in case
                rpm_streams[rpm] = (module['data']['name'], str(module['data']['stream']))

        self.log.debug('Installed modular RPMs detected:')
        for rpm in sorted(rpms):
            if rpm in rpm_streams:
                module, stream = rpm_streams[rpm]
                self.log.debug('    {n} (module: {m}, stream: {s})'.format(n=rpm, m=module, s=stream))
                self.produce(InstalledRPMModuleMapping(name=rpm, module=module, stream=stream))
