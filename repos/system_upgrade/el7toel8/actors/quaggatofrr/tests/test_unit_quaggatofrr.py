import contextlib
import os
import shutil

from leapp.libraries.actor import quaggatofrr

ACTIVE_DAEMONS = ['bgpd', 'ospfd', 'zebra']
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
FROM_DIR = '/tmp/from_dir/'
TO_DIR = '/tmp/to_dir/'
CONFIG_DATA = {
    'bgpd': '--daemon -A 10.10.100.1',
    'isisd': '--daemon -A ::1',
    'ospf6d': '-A ::1',
    'ospfd': '-A 127.0.0.1',
    'ripd': '-A 127.0.0.1',
    'ripngd': '-A ::1',
    'zebra': '-s 90000000 --daemon -A 127.0.0.1'
}


@contextlib.contextmanager
def _create_mock_files():
    try:
        os.mkdir(FROM_DIR)
        os.mkdir(TO_DIR)

        for num in range(1, 10):
            full_path = "{}test_file_{}".format(FROM_DIR, num)
            with open(full_path, 'w') as fp:
                fp.write("test_file_{}".format(num))
        yield
    finally:
        shutil.rmtree(FROM_DIR)
        shutil.rmtree(TO_DIR)


def test_copy_config_files():
    with _create_mock_files():
        quaggatofrr._copy_config_files(FROM_DIR, TO_DIR)
        conf_files = os.listdir(TO_DIR)
        for file_name in conf_files:
            full_path = os.path.join(TO_DIR, file_name)
            assert os.path.isfile(full_path)


def test_get_config_data():
    conf_data = quaggatofrr._get_config_data(
        os.path.join(CUR_DIR, 'files/quagga')
    )

    assert 'babels' not in conf_data
    assert conf_data['bgpd'] == CONFIG_DATA['bgpd']
    assert conf_data['isisd'] == CONFIG_DATA['isisd']
    assert conf_data['ospf6d'] == CONFIG_DATA['ospf6d']
    assert conf_data['ospfd'] == CONFIG_DATA['ospfd']
    assert conf_data['ripd'] == CONFIG_DATA['ripd']
    assert conf_data['ripngd'] == CONFIG_DATA['ripngd']
    assert conf_data['zebra'] == CONFIG_DATA['zebra']


def test_edit_new_config():
    # writing the data to the new config file
    data = quaggatofrr._edit_new_config(
        os.path.join(CUR_DIR, 'files/daemons'),
        ACTIVE_DAEMONS,
        CONFIG_DATA
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
