import re

from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

RE_MACHINE_TYPE = re.compile(r'^processor.*\smachine\s*=\s*([0-9]+)')


def _get_cpuinfo():
    """Return lines from /proc/cpuinfo."""
    # Expecting the file exists on earch system, skipping any check
    with open('/proc/cpuinfo', 'rb') as fp:
        return fp.readlines()


def process():
    cpuinfo = CPUInfo()

    machine_types = [RE_MACHINE_TYPE.findall(line) for line in _get_cpuinfo()]
    machine_types = [i[0] for i in machine_types if i]
    if machine_types:
        # machine type should be same for all found cpus
        cpuinfo.machine_type = int(machine_types[0])
    api.produce(cpuinfo)
