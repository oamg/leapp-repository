from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import PamUserDbLocation


def _convert_db(db_path):
    cmd = ['db_converter', '--src', f'{db_path}.db', '--dest', f'{db_path}.gdbm']
    try:
        run(cmd)
    except (CalledProcessError, OSError) as e:
        # As the db_converter does not remove the original DB after conversion or upon failure,
        # interrupt the upgrade, keeping the original DBs.
        # If all DBs are successfully converted, the leftover DBs are removed in the removeoldpamuserdb actor.
        raise StopActorExecutionError(
            'Cannot convert pam_userdb database.',
            details={'details': '{}: {}'.format(str(e), e.stderr)}
        )


def process():
    msg = next(api.consume(PamUserDbLocation), None)
    if not msg:
        raise StopActorExecutionError('Expected PamUserDbLocation, but got None')

    if msg.locations:
        for location in msg.locations:
            _convert_db(location)
