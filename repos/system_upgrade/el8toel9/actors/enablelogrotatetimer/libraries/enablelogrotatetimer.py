from leapp.libraries.common.systemd import enable_unit
from leapp.libraries.stdlib import api, CalledProcessError

LOGROTATE_TIMER = 'logrotate.timer'


def process():
    try:
        enable_unit(LOGROTATE_TIMER)
    except CalledProcessError as e:
        api.current_logger().error(
            "Failed to enable {}: {}".format(LOGROTATE_TIMER, e)
        )
