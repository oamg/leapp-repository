import os

from leapp.libraries.actor import networkmanagerreadconfig

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_nm_with_dhcp():
    config = networkmanagerreadconfig.read_nm_config(file_path=os.path.join(CUR_DIR, 'files/nm_cfg_with_dhcp'))
    parser = networkmanagerreadconfig.parse_nm_config(config)

    assert config
    assert parser
    assert parser.has_option('main', 'dhcp')


def test_nm_without_dhcp():
    config = networkmanagerreadconfig.read_nm_config(file_path=os.path.join(CUR_DIR, 'files/nm_cfg_without_dhcp'))
    parser = networkmanagerreadconfig.parse_nm_config(config)

    assert config
    assert parser
    assert not parser.has_option('main', 'dhcp')


def test_nm_with_error():
    config = networkmanagerreadconfig.read_nm_config(file_path=os.path.join(CUR_DIR, 'files/nm_cfg_file_error'))
    parser = networkmanagerreadconfig.parse_nm_config(config)

    assert config
    assert parser
    assert not parser.has_section('main')
