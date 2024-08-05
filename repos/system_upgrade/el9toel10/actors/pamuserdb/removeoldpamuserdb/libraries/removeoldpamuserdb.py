from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import PamUserDbLocation


def _remove_db(db_path):
    cmd = ['rm', '-f', f'{db_path}.db']
    try:
        run(cmd)
    except (CalledProcessError, OSError) as e:
        api.current_logger().error(
            'Failed to remove {}.db: {}'.format(
                db_path, e
            )
        )


def process():
    msg = next(api.consume(PamUserDbLocation), None)
    if not msg:
        raise StopActorExecutionError('Expected PamUserDbLocation, but got None')

    if msg.locations:
        for location in msg.locations:
            _remove_db(location)
