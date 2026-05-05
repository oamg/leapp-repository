import os

import pytest

from leapp.libraries.actor import multipathconfread
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MultipathConfFacts9to10, MultipathConfig9to10, MultipathInfo

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')


def build_config(pathname, config_dir=None, bindings_file=None, wwids_file=None,
                 prkeys_file=None, has_getuid=False):
    return MultipathConfig9to10(
        pathname=pathname,
        config_dir=config_dir,
        bindings_file=bindings_file,
        wwids_file=wwids_file,
        prkeys_file=prkeys_file,
        has_getuid=has_getuid,
    )


def assert_config(config, expected):
    assert config.pathname == expected.pathname
    assert config.config_dir == expected.config_dir
    assert config.bindings_file == expected.bindings_file
    assert config.wwids_file == expected.wwids_file
    assert config.prkeys_file == expected.prkeys_file
    assert config.has_getuid == expected.has_getuid


default_rhel9_conf = build_config(
    os.path.join(TEST_DIR, 'default_rhel9.conf'))

empty_conf = build_config(
    os.path.join(TEST_DIR, 'empty.conf'))

getuid_defaults_conf = build_config(
    os.path.join(TEST_DIR, 'getuid_defaults.conf'), has_getuid=True)

getuid_devices_conf = build_config(
    os.path.join(TEST_DIR, 'getuid_devices.conf'), has_getuid=True)

getuid_overrides_conf = build_config(
    os.path.join(TEST_DIR, 'getuid_overrides.conf'), has_getuid=True)

all_options_conf = build_config(
    os.path.join(TEST_DIR, 'all_options.conf'),
    config_dir='/etc/multipath/conf.d',
    bindings_file='/etc/multipath/bindings',
    wwids_file='/etc/multipath/wwids',
    prkeys_file='/etc/multipath/prkeys',
    has_getuid=True)

no_defaults_conf = build_config(
    os.path.join(TEST_DIR, 'no_defaults.conf'), has_getuid=True)

complicated_conf = build_config(
    os.path.join(TEST_DIR, 'complicated.conf'),
    config_dir='/etc/multipath/conf.d',
    bindings_file='/etc/multipath/bindings',
    wwids_file='/etc/multipath/wwids',
    prkeys_file='/etc/multipath/prkeys')


def test_parse_config():
    test_map = {'default_rhel9.conf': default_rhel9_conf,
                'empty.conf': empty_conf,
                'getuid_defaults.conf': getuid_defaults_conf,
                'getuid_devices.conf': getuid_devices_conf,
                'getuid_overrides.conf': getuid_overrides_conf,
                'all_options.conf': all_options_conf,
                'no_defaults.conf': no_defaults_conf,
                'complicated.conf': complicated_conf}
    for config_name, expected_data in test_map.items():
        config = multipathconfread._parse_config(os.path.join(TEST_DIR, config_name))
        assert config
        assert_config(config, expected_data)


extra_slash_conf = build_config(
    os.path.join(TEST_DIR, 'extra_slash.conf'),
    config_dir=os.path.join(TEST_DIR, '/etc/multipath/conf.d/'))

missing_dir_conf = build_config(
    os.path.join(TEST_DIR, 'missing_dir.conf'),
    config_dir=os.path.join(TEST_DIR, 'missing'))

empty_dir_conf = build_config(
    os.path.join(TEST_DIR, 'empty_dir.conf'),
    config_dir=os.path.join(TEST_DIR, 'conf3.d'))

config_dir_conf = build_config(
    os.path.join(TEST_DIR, 'config_dir.conf'),
    config_dir=os.path.join(TEST_DIR, 'conf1.d'))

bindings_set_conf = build_config(
    os.path.join(TEST_DIR, 'conf1.d/bindings_set.conf'),
    bindings_file='/etc/multipath/bindings')

empty1_conf = build_config(
    os.path.join(TEST_DIR, 'conf1.d/empty.conf'))

all_set_in_dir_conf = build_config(
    os.path.join(TEST_DIR, 'all_set_in_dir.conf'),
    config_dir=os.path.join(TEST_DIR, 'conf2.d'))

getuid_set_conf = build_config(
    os.path.join(TEST_DIR, 'conf2.d/getuid_set.conf'),
    has_getuid=True)

set_files_conf = build_config(
    os.path.join(TEST_DIR, 'conf2.d/set_files.conf'),
    bindings_file='/etc/multipath/bindings',
    wwids_file='/etc/multipath/wwids',
    prkeys_file='/etc/multipath/prkeys')


def mock_parse_config(path):
    """Convert config_dir into full pathname"""
    conf = multipathconfread._parse_config_orig(path)
    if not conf:
        return None
    if conf.config_dir:
        conf.config_dir = os.path.join(TEST_DIR, conf.config_dir)
    return conf


def mock_parse_config_dir(path):
    assert os.path.normpath(path) == '/etc/multipath/conf.d'
    return []


@pytest.mark.parametrize(
    ('primary_config', 'expected_config'),
    [
        ('all_options.conf', all_options_conf),
        ('default_rhel9.conf', default_rhel9_conf),
        ('extra_slash.conf', extra_slash_conf),
    ]
)
def test_get_primary_facts_default_config_dir(monkeypatch, primary_config, expected_config):
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: True)
    monkeypatch.setattr(multipathconfread, '_parse_config_dir', mock_parse_config_dir)

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    config_to_use = os.path.join(TEST_DIR, primary_config)
    multipathconfread.scan_and_emit_multipath_info(config_to_use)

    assert produce_mock.called

    general_info = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathInfo)]
    assert len(general_info) == 1
    assert general_info[0].is_configured
    assert general_info[0].config_dir == '/etc/multipath/conf.d'
    assert general_info[0].bindings_file == '/etc/multipath/bindings'
    assert general_info[0].wwids_file == '/etc/multipath/wwids'
    assert general_info[0].prkeys_file == '/etc/multipath/prkeys'

    msgs = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathConfFacts9to10)]
    assert len(msgs) == 1

    actual_configs = msgs[0].configs
    assert len(actual_configs) == 1

    assert_config(actual_configs[0], expected_config)


@pytest.mark.parametrize(
    ('primary_config', 'expected_configs'),
    [
        ('missing_dir.conf', [missing_dir_conf]),
        ('empty_dir.conf', [empty_dir_conf]),
        ('config_dir.conf', [config_dir_conf, bindings_set_conf, empty1_conf]),
        ('all_set_in_dir.conf', [all_set_in_dir_conf, getuid_set_conf, set_files_conf]),
    ]
)
def test_get_facts_with_config_dir(monkeypatch, primary_config, expected_configs):
    monkeypatch.setattr(multipathconfread, '_parse_config_orig', multipathconfread._parse_config, raising=False)
    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse_config)
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: False)

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    config_to_use = os.path.join(TEST_DIR, primary_config)
    multipathconfread.scan_and_emit_multipath_info(config_to_use)

    assert produce_mock.called

    general_info = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathInfo)]
    assert len(general_info) == 1
    assert general_info[0].is_configured
    assert not general_info[0].config_dir

    msgs = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathConfFacts9to10)]
    assert len(msgs) == 1

    actual_configs = msgs[0].configs
    assert len(actual_configs) == len(expected_configs)

    for actual_config, expected_config in zip(actual_configs, expected_configs):
        assert_config(actual_config, expected_config)


def test_file_locations_default(monkeypatch):
    """Default or unset file locations should be set on MultipathInfo."""
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: False)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: False)
    monkeypatch.setattr(multipathconfread, '_parse_config_dir', mock_parse_config_dir)

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    config_to_use = os.path.join(TEST_DIR, 'all_options.conf')
    multipathconfread.scan_and_emit_multipath_info(config_to_use)

    general_info = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathInfo)]
    assert len(general_info) == 1
    assert general_info[0].bindings_file == '/etc/multipath/bindings'
    assert general_info[0].wwids_file == '/etc/multipath/wwids'
    assert general_info[0].prkeys_file == '/etc/multipath/prkeys'


def test_file_locations_nondefault(monkeypatch):
    """Non-default file locations should NOT be set on MultipathInfo."""
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: False)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: False)
    monkeypatch.setattr(multipathconfread, '_parse_config_dir', mock_parse_config_dir)

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    # Use a config that sets files to non-default paths
    def mock_parse(path):
        return MultipathConfig9to10(
            pathname=path,
            bindings_file='/tmp/bindings',
            wwids_file='/tmp/wwids',
            prkeys_file='/tmp/prkeys',
        )

    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse)

    multipathconfread.scan_and_emit_multipath_info('/etc/multipath.conf')

    general_info = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathInfo)]
    assert len(general_info) == 1
    # Non-default file locations should not be set on MultipathInfo
    assert general_info[0].bindings_file is None
    assert general_info[0].wwids_file is None
    assert general_info[0].prkeys_file is None


def test_file_locations_secondary_overrides(monkeypatch):
    """Last non-None value wins for file locations across configs."""
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: False)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: False)

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    primary = MultipathConfig9to10(
        pathname='/etc/multipath.conf',
        bindings_file='/tmp/bindings',
    )

    secondary = MultipathConfig9to10(
        pathname='/etc/multipath/conf.d/secondary.conf',
        bindings_file='/etc/multipath/bindings',
    )

    def mock_parse(path):
        return primary

    def mock_parse_dir(config_dir):
        return [secondary]

    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse)
    monkeypatch.setattr(multipathconfread, '_parse_config_dir', mock_parse_dir)

    multipathconfread.scan_and_emit_multipath_info('/etc/multipath.conf')

    general_info = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathInfo)]
    assert len(general_info) == 1
    # Secondary overrides primary to default, so it should be set
    assert general_info[0].bindings_file == '/etc/multipath/bindings'


def test_check_socket_activation(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    assert multipathconfread._check_socket_activation() is True

    monkeypatch.setattr(os.path, 'exists', lambda path: False)
    assert multipathconfread._check_socket_activation() is False


def test_check_dm_nvme_multipathing_no_module(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)
    assert multipathconfread._check_dm_nvme_multipathing() is False


def test_check_dm_nvme_multipathing_disabled(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(multipathconfread, 'open',
                        lambda path, mode='r': _mock_open('N'), raising=False)
    assert multipathconfread._check_dm_nvme_multipathing() is True


def test_check_dm_nvme_multipathing_enabled(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(multipathconfread, 'open',
                        lambda path, mode='r': _mock_open('Y'), raising=False)
    assert multipathconfread._check_dm_nvme_multipathing() is False


class _mock_open:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self._content


def test_system_fields_on_primary(monkeypatch):
    monkeypatch.setattr(multipathconfread, 'is_processable', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_socket_activation', lambda: True)
    monkeypatch.setattr(multipathconfread, '_check_dm_nvme_multipathing', lambda: True)
    monkeypatch.setattr(multipathconfread, '_parse_config_dir', lambda config_dir: [])

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    actor_mock = CurrentActorMocked(src_ver='9.6', dst_ver='10.0')
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    config_to_use = os.path.join(TEST_DIR, 'default_rhel9.conf')
    multipathconfread.scan_and_emit_multipath_info(config_to_use)

    assert produce_mock.called

    msgs = [msg for msg in produce_mock.model_instances if isinstance(msg, MultipathConfFacts9to10)]
    assert len(msgs) == 1

    configs = msgs[0].configs
    assert len(configs) == 1

    primary = configs[0]
    assert primary.has_socket_activation is True
    assert primary.has_dm_nvme_multipathing is True
