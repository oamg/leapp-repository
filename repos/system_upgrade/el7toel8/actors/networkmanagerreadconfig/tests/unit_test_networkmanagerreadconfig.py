from leapp.libraries.actor import library
from leapp.models import NetworkManagerConfig


def test_nm_with_dhcp():
    config = library.read_nm_config(file_path='tests/files/nm_cfg_with_dhcp')
    parser = library.parse_nm_config(config)

    assert config
    assert parser
    assert parser.has_option('main', 'dhcp')


def test_nm_without_dhcp():
    config = library.read_nm_config(file_path='tests/files/nm_cfg_without_dhcp')
    parser = library.parse_nm_config(config)

    assert config
    assert parser
    assert not parser.has_option('main', 'dhcp')


def test_nm_with_error():
    config = library.read_nm_config(file_path='tests/files/nm_cfg_file_error')
    parser = library.parse_nm_config(config)

    assert config
    assert parser
    assert not parser.has_section('main')
