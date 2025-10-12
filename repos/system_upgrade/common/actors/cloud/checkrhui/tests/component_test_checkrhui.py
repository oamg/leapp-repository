import itertools
import os
from collections import defaultdict
from enum import Enum

import pytest

from leapp import reporting
from leapp.configs.common.rhui import (
    all_rhui_cfg,
    RhuiCloudProvider,
    RhuiCloudVariant,
    RhuiSourcePkgs,
    RhuiTargetPkgs,
    RhuiTargetRepositoriesToUse,
    RhuiUpgradeFiles,
    RhuiUseConfig
)
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkrhui as checkrhui_lib
from leapp.libraries.common import rhsm, rhui
from leapp.libraries.common.rhui import mk_rhui_setup, RHUIFamily
from leapp.libraries.common.testutils import (
    _make_default_config,
    create_report_mocked,
    CurrentActorMocked,
    produce_mocked
)
from leapp.libraries.stdlib import api
from leapp.models import (
    InstalledRPM,
    RHUIInfo,
    RPM,
    RpmTransactionTasks,
    TargetRepositories,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo,
    TargetUserSpacePreupgradeTasks
)

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def mk_pkg(name):
    return RPM(name=name, version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')


def mk_setup_info():
    pre_tasks = TargetRHUIPreInstallTasks()
    post_tasks = TargetRHUIPostInstallTasks()
    return TargetRHUISetupInfo(preinstall_tasks=pre_tasks, postinstall_tasks=post_tasks)


def iter_known_rhui_setups():
    for upgrade_path, providers in rhui.RHUI_CLOUD_MAP.items():
        for provider_variant, variant_description in providers.items():
            src_clients = variant_description['src_pkg']
            if isinstance(src_clients, str):
                src_clients = {src_clients, }

            yield provider_variant, upgrade_path, src_clients


def mk_cloud_map(variants):
    upg_path = {}
    for variant_desc in variants:
        provider, desc = next(iter(variant_desc.items()))
        upg_path[provider] = desc
    return upg_path


@pytest.mark.parametrize(
    ('extra_pkgs', 'rhui_setups', 'expected_result'),
    [
        (
            ['client'],
            {RHUIFamily('provider'): [mk_rhui_setup(clients={'client'})]},
            RHUIFamily('provider')
        ),
        (
            ['client'],
            {RHUIFamily('provider'): [mk_rhui_setup(clients={'missing_client'})]},
            None
        ),
        (
            ['clientA', 'clientB'],
            {RHUIFamily('provider'): [mk_rhui_setup(clients={'clientB'})]},
            RHUIFamily('provider')
        ),
        (
            ['clientA', 'clientB'],
            {
                RHUIFamily('provider'): [mk_rhui_setup(clients={'clientA'})],
                RHUIFamily('provider+'): [mk_rhui_setup(clients={'clientA', 'clientB'})],
            },
            RHUIFamily('provider+')
        ),
        (
            ['client'],
            {
                RHUIFamily('providerA'): [mk_rhui_setup(clients={'client'})],
                RHUIFamily('providerB'): [mk_rhui_setup(clients={'client'})],
            },
            StopActorExecutionError
        ),
    ]
)
def test_determine_rhui_src_variant(monkeypatch, extra_pkgs, rhui_setups, expected_result):
    actor = CurrentActorMocked(src_ver='7.9', config=_make_default_config(all_rhui_cfg))
    monkeypatch.setattr(api, 'current_actor', actor)
    installed_pkgs = {'zip', 'zsh', 'bash', 'grubby'}.union(set(extra_pkgs))

    if expected_result and not isinstance(expected_result, RHUIFamily):  # An exception
        with pytest.raises(expected_result) as err:
            checkrhui_lib.find_rhui_setup_matching_src_system(installed_pkgs, rhui_setups)
        assert 'ambiguous' in str(err)
        return

    variant_setup_pair = checkrhui_lib.find_rhui_setup_matching_src_system(installed_pkgs, rhui_setups)
    if not expected_result:
        assert variant_setup_pair == expected_result
    else:
        variant = variant_setup_pair[0]
        assert variant == expected_result


@pytest.mark.parametrize(
    ('extra_pkgs', 'target_rhui_setup', 'should_inhibit'),
    [
        (['pkg'], mk_rhui_setup(leapp_pkg='pkg'), False),
        ([], mk_rhui_setup(leapp_pkg='pkg'), True),
    ]
)
def test_inhibit_on_missing_leapp_rhui_pkg(monkeypatch, extra_pkgs, target_rhui_setup, should_inhibit):
    installed_pkgs = set(['bash', 'zsh', 'zip'] + extra_pkgs)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkrhui_lib.inhibit_if_leapp_pkg_to_access_target_missing(installed_pkgs,
                                                                RHUIFamily('rhui-variant'),
                                                                target_rhui_setup)
    assert bool(reporting.create_report.called) == should_inhibit


def are_setup_infos_eq(actual, expected):
    eq = True
    eq &= actual.enable_only_repoids_in_copied_files == expected.enable_only_repoids_in_copied_files
    eq &= actual.files_supporting_client_operation == expected.files_supporting_client_operation
    eq &= actual.preinstall_tasks.files_to_remove == expected.preinstall_tasks.files_to_remove
    eq &= actual.preinstall_tasks.files_to_copy_into_overlay == expected.preinstall_tasks.files_to_copy_into_overlay
    eq &= actual.postinstall_tasks.files_to_copy == expected.postinstall_tasks.files_to_copy
    return eq


@pytest.mark.parametrize(
    ('provider', 'should_mutate'),
    [
        (RHUIFamily(rhui.RHUIProvider.GOOGLE), True),
        (RHUIFamily(rhui.RHUIProvider.GOOGLE, variant=rhui.RHUIVariant.SAP), True),
        (RHUIFamily('azure'), False),
    ]
)
def test_google_specific_customization(provider, should_mutate):
    setup_info = mk_setup_info()
    checkrhui_lib.customize_rhui_setup_for_gcp(provider, setup_info)

    if should_mutate:
        assert setup_info != mk_setup_info()
    else:
        assert setup_info == mk_setup_info()


@pytest.mark.parametrize(
    ('rhui_family', 'target_major', 'should_mutate'),
    [
        (RHUIFamily(rhui.RHUIProvider.AWS), '8', False),
        (RHUIFamily(rhui.RHUIProvider.AWS), '9', True),
        (RHUIFamily(rhui.RHUIProvider.AWS, variant=rhui.RHUIVariant.SAP), '9', True),
        (RHUIFamily('azure'), '9', False),
    ]
)
def test_aws_specific_customization(monkeypatch, rhui_family, target_major, should_mutate):
    dst_ver = '{major}.0'.format(major=target_major)
    actor = CurrentActorMocked(dst_ver=dst_ver, config=_make_default_config(all_rhui_cfg))
    monkeypatch.setattr(api, 'current_actor', actor)

    setup_info = mk_setup_info()
    checkrhui_lib.customize_rhui_setup_for_aws(rhui_family, setup_info)

    was_mutated = not are_setup_infos_eq(setup_info, mk_setup_info())
    assert should_mutate == was_mutated


def produce_rhui_info_to_setup_target(monkeypatch):
    source_rhui_setup = mk_rhui_setup(
        clients={'src_pkg'},
        leapp_pkg='leapp_pkg',
        mandatory_files=[('src_file1', '/etc'), ('src_file2', '/var')],
    )

    target_rhui_setup = mk_rhui_setup(
        clients={'target_pkg'},
        leapp_pkg='leapp_pkg',
        mandatory_files=[('target_file1', '/etc'), ('target_file2', '/var')],
    )

    monkeypatch.setattr(api, 'get_common_folder_path', lambda dummy: 'common_folder')
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkrhui_lib.produce_rhui_info_to_setup_target('provider', source_rhui_setup, target_rhui_setup)

    assert len(api.produce.model_instances) == 1

    rhui_info = api.produce.model_instances[0]
    assert rhui_info.provider == 'provider'
    assert rhui_info.src_client_pkg_names == ['src_pkg']
    assert rhui_info.target_client_pkg_names == ['target_pkg']

    setup_info = rhui_info.target_client_setup_info

    expected_copies = {
        ('common_folder/provider/target_file1', '/etc'),
        ('common_folder/provider/target_file2', '/var')
    }
    actual_copies = {(instr.src, instr.dst) for instr in setup_info.preinstall_tasks.files_to_copy_in}

    assert expected_copies == actual_copies

    assert not setup_info.postinstall_tasks.files_to_copy


def test_produce_rpms_to_install_into_target(monkeypatch):
    source_clients = {'src_pkg'}
    target_clients = {'target_pkg'}

    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkrhui_lib.produce_rpms_to_install_into_target(source_clients, target_clients)

    assert len(api.produce.model_instances) == 2
    userspace_tasks, target_rpm_tasks = api.produce.model_instances[0], api.produce.model_instances[1]

    if isinstance(target_rpm_tasks, TargetUserSpacePreupgradeTasks):
        userspace_tasks, target_rpm_tasks = target_rpm_tasks, userspace_tasks

    assert 'target_pkg' in target_rpm_tasks.to_install
    assert 'src_pkg' in target_rpm_tasks.to_remove
    assert 'target_pkg' in userspace_tasks.install_rpms


@pytest.mark.parametrize('skip_rhsm', (True, False))
def test_inform_about_upgrade_with_rhui_without_no_rhsm(monkeypatch, skip_rhsm):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkrhui_lib.inform_about_upgrade_with_rhui_without_no_rhsm()

    assert bool(reporting.create_report.called) is not skip_rhsm


class ExpectedAction(Enum):
    NOTHING = 1  # Actor should not produce anything
    INHIBIT = 2
    PRODUCE = 3  # Actor should produce RHUI related info


# Scenarios to cover:
# 1. source client + NO_RHSM -> RPMs are produced, and setup info is produced
# 2. source client -> inhibit
# 3. leapp pkg missing -> inhibit
@pytest.mark.parametrize(
    ('extra_installed_pkgs', 'skip_rhsm', 'expected_action'),
    [
        (['src_pkg', 'leapp_pkg'], True, ExpectedAction.PRODUCE),  # Everything OK
        (['src_pkg', 'leapp_pkg'], False, ExpectedAction.INHIBIT),  # No --no-rhsm
        (['src_pkg'], True, ExpectedAction.INHIBIT),  # Missing leapp-rhui package
        ([], True, ExpectedAction.NOTHING)  # Not a RHUI system
    ]
)
def test_process(monkeypatch, extra_installed_pkgs, skip_rhsm, expected_action):
    known_setups = {
        RHUIFamily("rhui-variant"): [
            mk_rhui_setup(clients={"src_pkg"}, os_version="8"),
            mk_rhui_setup(
                clients={"target_pkg"},
                os_version="9",
                leapp_pkg="leapp_pkg",
                mandatory_files=[("file1", "/etc"), ("file2", "/var")],
            ),
        ]
    }

    installed_pkgs = {'zip', 'kernel-core', 'python'}.union(set(extra_installed_pkgs))
    installed_pkgs = [mk_pkg(pkg_name) for pkg_name in installed_pkgs]
    installed_rpms = InstalledRPM(items=installed_pkgs)

    monkeypatch.setattr(api, 'produce', produce_mocked())
    actor = CurrentActorMocked(msgs=[installed_rpms], config=_make_default_config(all_rhui_cfg))
    monkeypatch.setattr(api, 'current_actor', actor)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(rhui, 'RHUI_SETUPS', known_setups)

    checkrhui_lib.process()

    if expected_action == ExpectedAction.NOTHING:
        assert not api.produce.called
        assert not reporting.create_report.called
    elif expected_action == ExpectedAction.INHIBIT:
        assert not api.produce.called
        assert len(reporting.create_report.reports) == 1
    else:  # expected_action = ExpectedAction.PRODUCE
        assert not reporting.create_report.called
        assert len(api.produce.model_instances) == 3
        assert any(isinstance(pkg, RpmTransactionTasks) for pkg in api.produce.model_instances)
        assert any(isinstance(pkg, RHUIInfo) for pkg in api.produce.model_instances)
        assert any(isinstance(pkg, TargetUserSpacePreupgradeTasks) for pkg in api.produce.model_instances)


@pytest.mark.parametrize('is_target_setup_known', (False, True))
def test_unknown_target_rhui_setup(monkeypatch, is_target_setup_known):
    rhui_family = RHUIFamily('rhui-variant')
    known_setups = {
        rhui_family: [
            mk_rhui_setup(clients={'src_pkg'}, os_version='8'),
        ]
    }

    if is_target_setup_known:
        target_setup = mk_rhui_setup(clients={'target_pkg'}, os_version='9', leapp_pkg='leapp_pkg')
        known_setups[rhui_family].append(target_setup)

    installed_pkgs = {'zip', 'kernel-core', 'python', 'src_pkg', 'leapp_pkg'}
    installed_pkgs = [mk_pkg(pkg_name) for pkg_name in installed_pkgs]
    installed_rpms = InstalledRPM(items=installed_pkgs)

    monkeypatch.setattr(api, 'produce', produce_mocked())
    actor = CurrentActorMocked(msgs=[installed_rpms], config=_make_default_config(all_rhui_cfg))
    monkeypatch.setattr(api, 'current_actor', actor)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(rhui, 'RHUI_SETUPS', known_setups)

    if is_target_setup_known:
        checkrhui_lib.process()
        assert api.produce.called
    else:
        with pytest.raises(StopActorExecutionError):
            checkrhui_lib.process()


@pytest.mark.parametrize(
    ('setups', 'desired_minor', 'expected_setup'),
    [
        (
            [
                mk_rhui_setup(clients={'A'}, os_version='8.4', leapp_pkg='leapp-A'),
                mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
            ],
            8,
            mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
        ),
        (
            [
                mk_rhui_setup(clients={'A'}, os_version='8.4', leapp_pkg='leapp-A'),
                mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
            ],
            6,
            mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
        ),
        (
            [
                mk_rhui_setup(clients={'A'}, os_version='8.4', leapp_pkg='leapp-A'),
                mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
            ],
            5,
            mk_rhui_setup(clients={'A'}, os_version='8.4', leapp_pkg='leapp-A'),
        ),
        (
            [
                mk_rhui_setup(clients={'A'}, os_version='8.4', leapp_pkg='leapp-A'),
                mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
            ],
            3,
            mk_rhui_setup(clients={'A'}, os_version='8.6', leapp_pkg='leapp-B'),
        )
    ]
)
def test_select_chronologically_closest(monkeypatch, setups, desired_minor, expected_setup):
    setups = checkrhui_lib.select_chronologically_closest_setups(setups,
                                                                 desired_minor,
                                                                 lambda setup: setup.os_version[1],
                                                                 'source')
    assert len(setups) == 1
    setup = setups[0]

    assert setup == expected_setup


def test_config_overwrites_everything(monkeypatch):
    rhui_config = {
        RhuiUseConfig.name: True,
        RhuiSourcePkgs.name: ['client_source'],
        RhuiTargetPkgs.name: ['client_target'],
        RhuiCloudProvider.name: 'aws',
        RhuiUpgradeFiles.name: {
            '/root/file.repo': '/etc/yum.repos.d/'
        },
        RhuiTargetRepositoriesToUse.name: [
            'repoid_to_use'
        ]
    }
    all_config = {'rhui': rhui_config}

    actor = CurrentActorMocked(config=all_config)
    monkeypatch.setattr(api, 'current_actor', actor)

    function_calls = defaultdict(int)

    def mk_function_probe(fn_name):
        def probe(*args, **kwargs):
            function_calls[fn_name] += 1
        return probe

    monkeypatch.setattr(checkrhui_lib,
                        'emit_rhui_setup_tasks_based_on_config',
                        mk_function_probe('emit_rhui_setup_tasks_based_on_config'))
    monkeypatch.setattr(checkrhui_lib,
                        'stop_with_err_if_config_missing_fields',
                        mk_function_probe('stop_with_err_if_config_missing_fields'))
    monkeypatch.setattr(checkrhui_lib,
                        'produce_rpms_to_install_into_target',
                        mk_function_probe('produce_rpms_to_install_into_target'))
    monkeypatch.setattr(checkrhui_lib,
                        'request_configured_repos_to_be_enabled',
                        mk_function_probe('request_configured_repos_to_be_enabled'))

    checkrhui_lib.process()

    expected_function_calls = {
        'emit_rhui_setup_tasks_based_on_config': 1,
        'stop_with_err_if_config_missing_fields': 1,
        'produce_rpms_to_install_into_target': 1,
        'request_configured_repos_to_be_enabled': 1,
    }

    assert function_calls == expected_function_calls


def test_request_configured_repos_to_be_enabled(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())

    rhui_config = {
        RhuiUseConfig.name: True,
        RhuiSourcePkgs.name: ['client_source'],
        RhuiTargetPkgs.name: ['client_target'],
        RhuiCloudProvider.name: 'aws',
        RhuiUpgradeFiles.name: {
            '/root/file.repo': '/etc/yum.repos.d/'
        },
        RhuiTargetRepositoriesToUse.name: [
            'repoid1',
            'repoid2',
            'repoid3',
        ]
    }

    checkrhui_lib.request_configured_repos_to_be_enabled(rhui_config)

    assert api.produce.called
    assert len(api.produce.model_instances) == 1

    target_repos = api.produce.model_instances[0]
    assert isinstance(target_repos, TargetRepositories)
    assert not target_repos.rhel_repos

    custom_repoids = sorted(custom_repo_model.repoid for custom_repo_model in target_repos.custom_repos)
    assert custom_repoids == ['repoid1', 'repoid2', 'repoid3']


@pytest.mark.parametrize(
    ('upgrade_files', 'existing_files'),
    (
        (['/root/a', '/root/b'], ['/root/a', '/root/b']),
        (['/root/a', '/root/b'], ['/root/b']),
        (['/root/a', '/root/b'], []),
    )
)
def test_missing_files_in_config(monkeypatch, upgrade_files, existing_files):
    upgrade_files_map = dict((source_path, '/tmp/dummy') for source_path in upgrade_files)

    rhui_config = {
        RhuiUseConfig.name: True,
        RhuiSourcePkgs.name: ['client_source'],
        RhuiTargetPkgs.name: ['client_target'],
        RhuiCloudProvider.name: 'aws',
        RhuiCloudVariant.name: 'ordinary',
        RhuiUpgradeFiles.name: upgrade_files_map,
        RhuiTargetRepositoriesToUse.name: [
            'repoid_to_use'
        ]
    }

    monkeypatch.setattr(os.path, 'exists', lambda path: path in existing_files)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    should_error = (len(upgrade_files) != len(existing_files))
    if should_error:
        with pytest.raises(StopActorExecutionError):
            checkrhui_lib.emit_rhui_setup_tasks_based_on_config(rhui_config)
    else:
        checkrhui_lib.emit_rhui_setup_tasks_based_on_config(rhui_config)
        assert api.produce.called
        assert len(api.produce.model_instances) == 1

        rhui_info = api.produce.model_instances[0]
        assert isinstance(rhui_info, RHUIInfo)
        assert rhui_info.provider == 'aws'
        assert rhui_info.variant == 'ordinary'
        assert rhui_info.src_client_pkg_names == ['client_source']
        assert rhui_info.target_client_pkg_names == ['client_target']

        setup_info = rhui_info.target_client_setup_info
        assert not setup_info.bootstrap_target_client

        _copies_to_perform = setup_info.preinstall_tasks.files_to_copy_into_overlay
        copies_to_perform = sorted((copy.src, copy.dst) for copy in _copies_to_perform)
        expected_copies = sorted(zip(upgrade_files, itertools.repeat('/tmp/dummy')))

        assert copies_to_perform == expected_copies
