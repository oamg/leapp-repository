from leapp.exceptions import CalledProcessError, StopActorExecutionError
from leapp.libraries.stdlib import run


def prepare_yum_config():
    ''' Call tool bundled with leapp responsible to handle yum configuration files '''
    try:
        run(['handleyumconfig'])
    except CalledProcessError as e:
        raise StopActorExecutionError(
            'Migration of yum configuration failed.',
            details={'details': str(e)})
