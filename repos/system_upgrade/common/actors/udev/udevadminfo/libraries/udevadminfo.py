from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import UdevAdmInfoData


def process():
    try:
        out = run(['udevadm', 'info', '-e'])['stdout']
    except (CalledProcessError, OSError) as err:
        raise StopActorExecutionError(
            message=(
                "Unable to gather information about the system devices"
            ),
            details={
                'details': 'Failed to execute `udevadm info -e` command.',
                'error': str(err)
            }
        )
    api.produce(UdevAdmInfoData(db=out))
