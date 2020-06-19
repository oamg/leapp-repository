from leapp.libraries.stdlib import CalledProcessError, api, run
from leapp.models import QuaggaToFrrFacts

QUAGGA_DAEMONS = [
    'babeld',
    'bgpd',
    'isisd',
    'ospf6d',
    'ospfd',
    'ripd',
    'ripngd',
    'zebra'
]


def _check_service(name, state):
    try:
        run(['systemctl', 'is-{}'.format(state), name])
        api.current_logger().debug('{} is {}'.format(name, state))
    except CalledProcessError:
        api.current_logger().debug('{} is not {}'.format(name, state))
        return False

    return True


def process_daemons():
    active_daemons = [daemon for daemon in QUAGGA_DAEMONS if _check_service(daemon, 'active']
    enabled_daemons = [daemon for daemon in QUAGGA_DAEMONS if _check_service(daemon, 'enabled')]

    if active_daemons:
        api.current_logger().debug('active quaggadaemons: {}'.format(', '.join(active_daemons)))

    if enabled_daemons:
        api.current_logger().debug('enabled quaggadaemons: {}'.format(', '.join(enabled_daemons)))

    return QuaggaToFrrFacts(active_daemons=active_daemons, enabled_daemons=enabled_daemons)
