import contextlib
import os
import shutil

import pytest

from leapp.libraries.actor import quaggatofrr
from leapp.libraries.common.testutils import CurrentActorMocked

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


class MockedFilePointer(object):
    def __init__(self, orig_open, fname, mode='r'):
        self._orig_open = orig_open
        self.fname = fname
        self.mode = mode
        # we want always read only..
        self._fp = self._orig_open(fname, 'r')
        self._read = None
        self.written = None

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def read(self):
        self._read = self._fp.read()
        return self._read

    def write(self, data):
        if not self.written:
            self.written = data
        else:
            self.written += data


class MockedOpen(object):
    """
    This is mock for the open function. When called it creates
    the MockedFilePointer object.
    """

    def __init__(self):
        # currently we want to actually open the real files, we need
        # to mock other stuff related to file pointers / file objects
        self._orig_open = open
        self._open_called = []

    def __call__(self, fname, mode='r'):
        opened = MockedFilePointer(self._orig_open, fname, mode)
        self._open_called.append(opened)
        return opened

    def get_mocked_pointers(self, fname, mode=None):
        """
        Get list of MockedFilePointer objects with the specified fname.

        if the mode is set (expected 'r', 'rw', 'w' ..) discovered files are
        additionally filtered to match the same mode (same string).
        """
        fnames = [i for i in self._open_called if i.fname == fname]
        return fnames if not mode else [i for i in fnames if i.mode == mode]


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


@pytest.mark.parametrize('dst_ver', ['8.4', '8.5'])
def test_fix_commands(monkeypatch, dst_ver):
    monkeypatch.setattr(quaggatofrr, "BGPD_CONF_FILE", os.path.join(CUR_DIR, 'files/bgpd.conf'))
    monkeypatch.setattr(quaggatofrr.api, 'current_actor', CurrentActorMocked(dst_ver=dst_ver))
    monkeypatch.setattr(quaggatofrr, "open", MockedOpen(), False)
    quaggatofrr._fix_commands()

    fp_list = quaggatofrr.open.get_mocked_pointers(quaggatofrr.BGPD_CONF_FILE, "w")
    assert len(fp_list) == 1
    assert 'bgp extcommunity-list' in fp_list[0].written


def test_fix_commands_not_applied(monkeypatch):
    is_file_called = False

    def mocked_is_file(dummy):
        is_file_called = True
        return is_file_called

    monkeypatch.setattr(quaggatofrr.api, 'current_actor', CurrentActorMocked(dst_ver='8.3'))
    monkeypatch.setattr(os.path, 'isfile', mocked_is_file)
    monkeypatch.setattr(quaggatofrr, "open", MockedOpen(), False)
    quaggatofrr._fix_commands()
    assert not is_file_called
