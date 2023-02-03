from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import RoceDetected


def get_roce_nics_lines():
    """
    Return basic info about RoCE NICs using nmcli

    When RoCE is configured on the system, we should find Mellanox a device
    in the `nmcli` output, which is always specified after status line
    of an interface, e.g.:
        # nmcli
        ens1765: connected to ens1765
            "Mellanox MT27710"
            ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500
            inet4 192.168.0.1/16
            route4 192.168.0.1/16
            inet6 fe80::d8c5:3a67:1abb:dcca/64
            route6 fe80::/64
    In this case, the function returns the list of lines with RoCE NICs.
    So for the example above:
        ['ens1765: connected to ens1765']

    NOTE: It is unexpected that a NIC itself could contain a 'mellanox'
    substring. In such a case additional unexpected lines could be returned.
    However, as we are interested only about lines with 'connected to' and 'connecting'
    substrings, we know we will filter out any invalid lines later, so it's
    no problem for us.
    """
    # nmcli | grep --no-group-separator -B1 -i "mellanox" | sed -n 1~2p
    roce_nic_lines = []
    try:
        nmcli_output = run(['nmcli'], split=True)['stdout']
    except (CalledProcessError, OSError) as e:
        # this is theoretical
        # If the command fails, most likely the network is not configured
        # or it is not configured in a 'supported' way - definitely not
        # for RoCE.
        api.current_logger().warning(
            'Cannot examine network connections via NetworkManager.'
            ' Assuming RoCE is not present. Detail: {}'.format(str(e))
        )
        return roce_nic_lines

    for i, line in enumerate(nmcli_output):
        if 'mellanox' in line.lower() and i > 0:
            roce_nic_lines.append(nmcli_output[i-1].strip())
    return roce_nic_lines


def _parse_NIC(nmcli_line):
    return nmcli_line.split(':')[0]


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        # The check is valid only on S390X architecture
        return
    connected_nics = []
    connecting_nics = []
    for line in get_roce_nics_lines():
        if 'connected to' in line:
            connected_nics.append(_parse_NIC(line))
        elif 'connecting' in line:
            connecting_nics.append(_parse_NIC(line))
    if connected_nics or connecting_nics:
        api.produce(RoceDetected(
           roce_nics_connected=connected_nics,
           roce_nics_connecting=connecting_nics,
        ))
