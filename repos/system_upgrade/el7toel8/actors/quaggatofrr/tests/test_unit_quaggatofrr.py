import errno
import os

from leapp.libraries.stdlib import api
from leapp.libraries.actor import quaggatofrr

ACTIVE_DAEMONS = ['bgpd', 'ospfd', 'zebra']
CUR_DIR = os.path.dirname(os.path.abspath(__file__))


# Test for functions _get_config_data and _edit_new_config from quaggatofrr
def test_quaggatofrr():
    # Testing if _get_config_data can parse the config file correctly
    conf_data = quaggatofrr._get_config_data(
        os.path.join(CUR_DIR, 'files/quagga')
    )
    assert 'babels' not in conf_data
    assert conf_data['bgpd'] == '--daemon -A 10.10.100.1'
    assert conf_data['isisd'] == '--daemon -A ::1'
    assert conf_data['ospf6d'] == '-A ::1'
    assert conf_data['ospfd'] == '-A 127.0.0.1'
    assert conf_data['ripd'] == '-A 127.0.0.1'
    assert conf_data['ripngd'] == '-A ::1'
    assert conf_data['zebra'] == '-s 90000000 --daemon -A 127.0.0.1'

    # writing the data to the new config file
    data = quaggatofrr._edit_new_config(
        os.path.join(CUR_DIR, 'files/daemons'),
        ACTIVE_DAEMONS,
        conf_data
    )

    assert 'zebra=yes' in data
    assert 'bgpd=yes' in data
    assert 'ospfd=yes' in data
    assert 'zebra_options=("-s 90000000 --daemon -A 127.0.0.1")' in data
    assert 'bgpd_options=("--daemon -A 10.10.100.1")' in data
    assert 'ospfd_options=("-A 127.0.0.1")' in data
    assert 'ospf6d_options=("-A ::1")' in data
    assert 'ripd_options=("-A 127.0.0.1")' in data
    assert 'ripngd_options=("-A ::1")' in data
    assert 'isisd_options=("--daemon -A ::1")' in data
