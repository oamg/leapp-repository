from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import MemoryInfo


def _get_memoryinfo(filename='/proc/meminfo'):
    """ Returns dict of all memory information from /proc/meminfo file """

    try:
        with open(filename) as fp:
            # format of the lines: Key:  value unit
            # e.g.:                MemTotal:   1024 kB
            return dict((i.split()[0].rstrip(':'), int(i.split()[1])) for i in fp.readlines())
    except IOError:
        raise StopActorExecutionError(
            'Could not read memory values',
            details={'details': 'Error opening file {}'.format(filename)},
        )


def process():
    mem_info = _get_memoryinfo()
    if mem_info:
        api.produce(MemoryInfo(mem_total=mem_info['MemTotal']))
