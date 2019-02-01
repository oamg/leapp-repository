from subprocess import check_output

from leapp.actors import Actor
from leapp.models import InstalledRPM, RPM
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RpmScanner(Actor):
    """
    Provides data about installed RPM Packages.

    After collecting data from RPM query, a message with relevant data will be produced.
    """

    name = 'rpm_scanner'
    consumes = ()
    produces = (InstalledRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        output = check_output([
            '/bin/rpm',
            '-qa',
            '--queryformat',
            r'%{NAME}|%{VERSION}|%{RELEASE}|%|EPOCH?{%{EPOCH}}:{}||%|ARCH?{%{ARCH}}:{}||%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{(none)}|}|\n'
        ])
        result = InstalledRPM()
        for entry in output.split('\n'):
            entry = entry.strip()
            if not entry:
                continue
            name, version, release, epoch, arch, pgpsig = entry.split('|')
            result.items.append(RPM(
                name=name,
                version=version,
                epoch=epoch,
                arch=arch,
                release=release,
                pgpsig=pgpsig))
        self.produce(result)
