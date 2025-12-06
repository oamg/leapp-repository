import os

import pytest

from leapp.libraries.actor import scanlvmconfig
from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, LVMConfig, LVMConfigDevicesSection, RPM


@pytest.mark.parametrize(
    ("config_as_lines", "config_as_dict"),
    [
        ([], {}),
        (
            ['devices {\n',
             '\t# comment\n'
             '}\n'],
            {}
         ),
        (
            ['global {\n',
             'use_lvmetad = 1\n',
             '}\n'],
            {}
         ),
        (
            ['devices {\n',
             'filter = [ "r|/dev/cdrom|", "a|.*|" ]\n',
             'use_devicesfile=0\n',
             'devicesfile="file-name.devices"\n',
             '}'],
            {'filter': '[ "r|/dev/cdrom|", "a|.*|" ]',
             'use_devicesfile': '0',
             'devicesfile': 'file-name.devices'}
         ),
        (
            ['devices {\n',
             'use_devicesfile = 1\n',
             'devicesfile  =  "file-name.devices"\n',
             ' }\n'],
            {'use_devicesfile': '1',
             'devicesfile': 'file-name.devices'}
         ),
        (
            ['devices {\n',
             '  # comment\n',
             'use_devicesfile = 1 # comment\n',
             '#devicesfile =  "file-name.devices"\n',
             ' }\n'],
            {'use_devicesfile': '1'}
         ),
        (
            ['config {\n',
             '# configuration section\n',
             '\tabort_on_errors = 1\n',
             '\tprofile_dir = "/etc/lvm/prifile\n',
             '}\n',
             'devices {\n',
             '  \n',
             '\tfilter =  ["a|.*|"] \n',
             '\tuse_devicesfile=0\n',
             '}\n',
             'allocation {\n',
             '\tcling_tag_list = [ "@site1", "@site2" ]\n',
             '\tcache_settings {\n',
             '\t}\n',
             '}\n'
             ],
            {'filter': '["a|.*|"]', 'use_devicesfile': '0'}
         ),
    ]

)
def test_lvm_config_devices_parser(config_as_lines, config_as_dict):
    lvm_config = scanlvmconfig._lvm_config_devices_parser(config_as_lines)
    assert lvm_config == config_as_dict


def test_scan_when_lvm_not_installed(monkeypatch):
    def isfile_mocked(_):
        assert False

    def read_config_lines_mocked(_):
        assert False

    msgs = [
        DistributionSignedRPM(items=[])
    ]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', isfile_mocked)
    monkeypatch.setattr(scanlvmconfig, '_read_config_lines', read_config_lines_mocked)

    scanlvmconfig.scan()

    assert not api.produce.called


@pytest.mark.parametrize(
    ('source_major_version', 'devices_section_dict', 'produced_devices_section'),
    [
        ('8', {}, LVMConfigDevicesSection(use_devicesfile=False)),
        ('9', {}, LVMConfigDevicesSection(use_devicesfile=True)),
        ('8', {
            'use_devicesfile': '0',
        }, LVMConfigDevicesSection(use_devicesfile=False,
                                   devicesfile='system.devices')
         ),
        ('9', {
            'use_devicesfile': '0',
            'devicesfile': 'file-name.devices'
        }, LVMConfigDevicesSection(use_devicesfile=False,
                                   devicesfile='file-name.devices')
         ),

        ('8', {
            'use_devicesfile': '1',
            'devicesfile': 'file-name.devices'
        }, LVMConfigDevicesSection(use_devicesfile=True,
                                   devicesfile='file-name.devices')
         ),
        ('9', {
            'use_devicesfile': '1',
        }, LVMConfigDevicesSection(use_devicesfile=True,
                                   devicesfile='system.devices')
         ),

    ]

)
def test_scan_when_lvm_installed(monkeypatch, source_major_version, devices_section_dict, produced_devices_section):

    def isfile_mocked(file):
        assert file == scanlvmconfig.LVM_CONFIG_PATH
        return True

    def read_config_lines_mocked(file):
        assert file == scanlvmconfig.LVM_CONFIG_PATH
        return ["test_line"]

    def lvm_config_devices_parser_mocked(lines):
        assert lines == ["test_line"]
        return devices_section_dict

    lvm_package = RPM(
        name='lvm2',
        version='2',
        release='1',
        epoch='1',
        packager='',
        arch='x86_64',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
    )

    msgs = [
        DistributionSignedRPM(items=[lvm_package])
    ]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_major_version)
    monkeypatch.setattr(os.path, 'isfile', isfile_mocked)
    monkeypatch.setattr(scanlvmconfig, '_read_config_lines', read_config_lines_mocked)
    monkeypatch.setattr(scanlvmconfig, '_lvm_config_devices_parser', lvm_config_devices_parser_mocked)

    scanlvmconfig.scan()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1

    produced_model = api.produce.model_instances[0]
    assert isinstance(produced_model, LVMConfig)
    assert produced_model.devices == produced_devices_section
