from leapp.libraries.stdlib import api
from leapp.models import MachineIdInfo

_MACHINE_ID_PATH = '/etc/machine-id'


def process():
    machine_id = None
    try:
        with open(_MACHINE_ID_PATH, 'r') as f:
            machine_id = f.read().rstrip('\n')
    except OSError as e:
        api.current_logger().warning('Failed to read {}: {}'.format(_MACHINE_ID_PATH, e))
    api.produce(MachineIdInfo(machine_id=machine_id))
