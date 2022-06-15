from collections import namedtuple

import pytest

import leapp.models
from leapp.libraries.common import dnfplugin
from leapp.libraries.common.config.version import get_major_version
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models.fields import Boolean
from leapp.topics import Topic


class DATADnfPluginDataTopic(Topic):
    name = 'data_dnf_plugin_data'


fields = leapp.models.fields

TaskData = namedtuple('TaskData', 'expected initdata')

TEST_INSTALL_PACKAGES = TaskData(
    expected=('install1', 'install2'),
    initdata=('install1', 'install2')
)
TEST_REMOVE_PACKAGES = TaskData(
    expected=('remove1', 'remove2'),
    initdata=('remove1', 'remove2'),
)
TEST_UPGRADE_PACKAGES = TaskData(
    expected=('upgrade1', 'upgrade2'),
    initdata=('upgrade1', 'upgrade2'),
)
TEST_ENABLE_MODULES = TaskData(
    expected=('enable1:stream1', 'enable2:stream2'),
    initdata=(
        leapp.models.Module(name='enable1', stream='stream1'),
        leapp.models.Module(name='enable2', stream='stream2'),
    )
)


class DATADnfPluginDataPkgsInfo(leapp.models.Model):
    topic = DATADnfPluginDataTopic
    local_rpms = fields.List(fields.String())
    to_install = fields.List(fields.StringEnum(choices=TEST_INSTALL_PACKAGES.expected))
    to_remove = fields.List(fields.StringEnum(choices=TEST_REMOVE_PACKAGES.expected))
    to_upgrade = fields.List(fields.StringEnum(choices=TEST_UPGRADE_PACKAGES.expected))
    modules_to_enable = fields.List(fields.StringEnum(choices=TEST_ENABLE_MODULES.expected))


TEST_ENABLE_REPOS_CHOICES = ('enabled_repo', 'BASEOS', 'APPSTREAM')


class BooleanEnum(fields.EnumMixin, Boolean):
    pass


class DATADnfPluginDataDnfConf(leapp.models.Model):
    topic = DATADnfPluginDataTopic
    allow_erasing = BooleanEnum(choices=[True])
    best = BooleanEnum(choices=[True])
    debugsolver = fields.Boolean()
    disable_repos = BooleanEnum(choices=[True])
    enable_repos = fields.List(fields.StringEnum(choices=TEST_ENABLE_REPOS_CHOICES))
    gpgcheck = fields.Boolean()
    platform_id = fields.StringEnum(choices=['platform:el8', 'platform:el9'])
    releasever = fields.String()
    installroot = fields.StringEnum(choices=['/installroot'])
    test_flag = fields.Boolean()


class DATADnfPluginDataRHUIAWS(leapp.models.Model):
    topic = DATADnfPluginDataTopic
    on_aws = fields.Boolean()
    region = fields.Nullable(fields.String())


class DATADnfPluginDataRHUI(leapp.models.Model):
    topic = DATADnfPluginDataTopic
    aws = fields.Model(DATADnfPluginDataRHUIAWS)


class DATADnfPluginData(leapp.models.Model):
    topic = DATADnfPluginDataTopic
    pkgs_info = fields.Model(DATADnfPluginDataPkgsInfo)
    dnf_conf = fields.Model(DATADnfPluginDataDnfConf)
    rhui = fields.Model(DATADnfPluginDataRHUI)


# Delete those models from leapp.models to 'unpolute' the module
del leapp.models.DATADnfPluginDataPkgsInfo
del leapp.models.DATADnfPluginDataDnfConf
del leapp.models.DATADnfPluginDataRHUI
del leapp.models.DATADnfPluginDataRHUIAWS
del leapp.models.DATADnfPluginData


_CONFIG_BUILD_TEST_DEFINITION = (
    #   Parameter, Input Data, Expected Fields with data
    ('debug', False, ('dnf_conf', 'debugsolver'), False),
    ('debug', True, ('dnf_conf', 'debugsolver'), True),
    ('target_repoids', TEST_ENABLE_REPOS_CHOICES, ('dnf_conf', 'enable_repos'), list(TEST_ENABLE_REPOS_CHOICES)),
    ('target_repoids', TEST_ENABLE_REPOS_CHOICES[0:1],
     ('dnf_conf', 'enable_repos'), list(TEST_ENABLE_REPOS_CHOICES[0:1])),
    ('target_repoids', TEST_ENABLE_REPOS_CHOICES[1:],
     ('dnf_conf', 'enable_repos'), list(TEST_ENABLE_REPOS_CHOICES[1:])),
    ('target_repoids', TEST_ENABLE_REPOS_CHOICES[2:],
     ('dnf_conf', 'enable_repos'), list(TEST_ENABLE_REPOS_CHOICES[2:])),
    ('test', False, ('dnf_conf', 'test_flag'), False),
    ('test', True, ('dnf_conf', 'test_flag'), True),
)


@pytest.mark.parametrize('used_target_version', ['8.4', '8.5', '9.0', '9.1'])
@pytest.mark.parametrize('parameter,input_value,test_path,expected_value', _CONFIG_BUILD_TEST_DEFINITION)
def test_build_plugin_data_variations(
    monkeypatch,
    used_target_version,
    parameter,
    input_value,
    test_path,
    expected_value,
):
    used_target_major_version = get_major_version(used_target_version)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver=used_target_version))
    inputs = {
        'target_repoids': ['BASEOS', 'APPSTREAM'],
        'debug': True,
        'test': True,
        'on_aws': False,
        'tasks': leapp.models.FilteredRpmTransactionTasks(
            to_install=TEST_INSTALL_PACKAGES.initdata,
            to_remove=TEST_REMOVE_PACKAGES.initdata,
            to_upgrade=TEST_UPGRADE_PACKAGES.initdata,
            modules_to_enable=TEST_ENABLE_MODULES.initdata
            )
    }
    inputs[parameter] = input_value
    created = DATADnfPluginData.create(
        dnfplugin.build_plugin_data(
            **inputs
        )
    )
    assert created.dnf_conf.platform_id == 'platform:el{}'.format(used_target_major_version)
    assert created.dnf_conf.releasever == used_target_version
    value = created
    for path in test_path:
        value = getattr(value, path)
    assert value == expected_value


def test_build_plugin_data(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='8.4'))
    # Use leapp to validate format and data
    created = DATADnfPluginData.create(
        dnfplugin.build_plugin_data(
            target_repoids=['BASEOS', 'APPSTREAM'],
            debug=True,
            test=True,
            on_aws=False,
            tasks=leapp.models.FilteredRpmTransactionTasks(
                to_install=TEST_INSTALL_PACKAGES.initdata,
                to_remove=TEST_REMOVE_PACKAGES.initdata,
                to_upgrade=TEST_UPGRADE_PACKAGES.initdata,
                modules_to_enable=TEST_ENABLE_MODULES.initdata
                )
            )
    )
    assert created.dnf_conf.debugsolver is True
    assert created.dnf_conf.test_flag is True
    assert created.rhui.aws.on_aws is False

    with pytest.raises(fields.ModelViolationError):
        DATADnfPluginData.create(
            dnfplugin.build_plugin_data(
                target_repoids=['BASEOS', 'APPSTREAM'],
                debug=True,
                test=True,
                on_aws=False,
                tasks=leapp.models.FilteredRpmTransactionTasks(
                    to_install=TEST_INSTALL_PACKAGES.initdata,
                    to_remove=TEST_REMOVE_PACKAGES.initdata,
                    to_upgrade=TEST_UPGRADE_PACKAGES.initdata,
                    # Enforcing the failure
                    modules_to_enable=(
                        leapp.models.Module(
                            name='broken', stream=None
                        ),
                    ),
                )
            )
        )
