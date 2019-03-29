from leapp.actors import Actor
from leapp.libraries.stdlib import run
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
        output = run([
            '/bin/rpm',
            '-qa',
            '--queryformat',
            r'%{NAME}|%{VERSION}|%{RELEASE}|%|EPOCH?{%{EPOCH}}:{(none)}||%|PACKAGER?{%{PACKAGER}}:{(none)}||%|'
            r'ARCH?{%{ARCH}}:{}||%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{(none)}|}|\n'
        ], split=True)['stdout']

        result = InstalledRPM()
        for entry in output:
            entry = entry.strip()
            if not entry:
                continue
            name, version, release, epoch, packager, arch, pgpsig = entry.split('|')
            result.items.append(RPM(
                name=name,
                version=version,
                epoch=epoch,
                packager=packager,
                arch=arch,
                release=release,
                pgpsig=pgpsig))
        self.produce(result)
