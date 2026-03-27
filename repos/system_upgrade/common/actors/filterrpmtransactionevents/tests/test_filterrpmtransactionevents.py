from leapp.models import (
    DistributionSignedRPM,
    FilteredRpmTransactionTasks,
    InstalledRPM,
    Module,
    RHUIInfo,
    RPM,
    RpmTransactionTasks,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo
)
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'
UNSIGNED_PACKAGER = 'Third Party <third@party.com>'


def _make_rpm(name, packager=RH_PACKAGER):
    return RPM(name=name, version='0.1', release='1.sm01', epoch='1',
               packager=packager, arch='noarch', pgpsig='SOME_PGP_SIG')


def _make_rhui_info(src_clients, target_clients, provider='azure'):
    setup_info = TargetRHUISetupInfo(
        preinstall_tasks=TargetRHUIPreInstallTasks(),
        postinstall_tasks=TargetRHUIPostInstallTasks(),
    )
    return RHUIInfo(
        provider=provider,
        src_client_pkg_names=src_clients,
        target_client_pkg_names=target_clients,
        target_client_setup_info=setup_info,
    )


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(FilteredRpmTransactionTasks)


def test_actor_execution_with_sample_data(current_actor_context):
    installed_rpm = [_make_rpm('sample01'), _make_rpm('sample02')]
    modules_to_enable = [Module(name='enable', stream='1'), Module(name='enable', stream='2')]
    modules_to_reset = [Module(name='reset', stream='1'), Module(name='reset', stream='2')]
    current_actor_context.feed(DistributionSignedRPM(items=installed_rpm))
    current_actor_context.feed(RpmTransactionTasks(
        to_remove=[rpm.name for rpm in installed_rpm],
        to_keep=[installed_rpm[0].name],
        modules_to_enable=modules_to_enable,
        modules_to_reset=modules_to_reset,
    ))
    current_actor_context.feed(RpmTransactionTasks(
        modules_to_enable=modules_to_enable,
        modules_to_reset=modules_to_reset,
    ))
    current_actor_context.run()
    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert result[0].to_keep == [installed_rpm[0].name]
    assert result[0].to_remove == [installed_rpm[1].name]

    assert len(result[0].modules_to_enable) == 2
    assert all(m.name == 'enable' for m in result[0].modules_to_enable)
    assert '1' in {m.stream for m in result[0].modules_to_enable}
    assert '2' in {m.stream for m in result[0].modules_to_enable}

    assert len(result[0].modules_to_reset) == 2
    assert all(m.name == 'reset' for m in result[0].modules_to_reset)
    assert '1' in {m.stream for m in result[0].modules_to_reset}
    assert '2' in {m.stream for m in result[0].modules_to_reset}


def test_rhui_source_client_treated_as_signed(current_actor_context):
    """Installed RHUI source clients should be removable even if they are not distribution-signed."""
    rhui_client_rpm = _make_rpm('rhui-azure-rhel8', packager=UNSIGNED_PACKAGER)
    signed_rpm = _make_rpm('sample01')

    current_actor_context.feed(DistributionSignedRPM(items=[signed_rpm]))
    current_actor_context.feed(InstalledRPM(items=[rhui_client_rpm, signed_rpm]))
    current_actor_context.feed(_make_rhui_info(['rhui-azure-rhel8'], ['rhui-azure-rhel9']))
    current_actor_context.feed(RpmTransactionTasks(to_remove=['rhui-azure-rhel8']))
    current_actor_context.run()

    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert 'rhui-azure-rhel8' in result[0].to_remove


def test_rhui_source_client_not_installed_is_ignored(current_actor_context):
    """RHUI source clients that are not installed should not be added to the installed set."""
    signed_rpm = _make_rpm('sample01')

    current_actor_context.feed(DistributionSignedRPM(items=[signed_rpm]))
    current_actor_context.feed(InstalledRPM(items=[signed_rpm]))
    current_actor_context.feed(_make_rhui_info(['rhui-azure-rhel8'], ['rhui-azure-rhel9']))
    current_actor_context.feed(RpmTransactionTasks(to_remove=['rhui-azure-rhel8']))
    current_actor_context.run()

    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert 'rhui-azure-rhel8' not in result[0].to_remove


def test_no_rhui_info_unsigned_pkg_not_removable(current_actor_context):
    """Without RHUIInfo, unsigned packages should not be removable (baseline behavior)."""
    unsigned_rpm = _make_rpm('some-unsigned-pkg', packager=UNSIGNED_PACKAGER)
    signed_rpm = _make_rpm('sample01')

    current_actor_context.feed(DistributionSignedRPM(items=[signed_rpm]))
    current_actor_context.feed(InstalledRPM(items=[unsigned_rpm, signed_rpm]))
    current_actor_context.feed(RpmTransactionTasks(to_remove=['some-unsigned-pkg']))
    current_actor_context.run()

    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert 'some-unsigned-pkg' not in result[0].to_remove


def test_rhui_multiple_source_clients(current_actor_context):
    """Multiple RHUI source clients should all be treated as signed when installed."""
    client_rpms = [
        _make_rpm('rhui-client-a', packager=UNSIGNED_PACKAGER),
        _make_rpm('rhui-client-b', packager=UNSIGNED_PACKAGER),
    ]

    current_actor_context.feed(DistributionSignedRPM(items=[]))
    current_actor_context.feed(InstalledRPM(items=client_rpms))
    current_actor_context.feed(_make_rhui_info(['rhui-client-a', 'rhui-client-b'], ['rhui-client-target']))
    current_actor_context.feed(RpmTransactionTasks(
        to_remove=['rhui-client-a', 'rhui-client-b'],
    ))
    current_actor_context.run()

    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert 'rhui-client-a' in result[0].to_remove
    assert 'rhui-client-b' in result[0].to_remove


def test_rhui_source_client_ends_up_in_upgrade_if_not_removed(current_actor_context):
    """An installed RHUI source client not in to_remove/to_install should be upgraded."""
    rhui_client_rpm = _make_rpm('rhui-azure-rhel8', packager=UNSIGNED_PACKAGER)

    current_actor_context.feed(DistributionSignedRPM(items=[]))
    current_actor_context.feed(InstalledRPM(items=[rhui_client_rpm]))
    current_actor_context.feed(_make_rhui_info(['rhui-azure-rhel8'], ['rhui-azure-rhel9']))
    current_actor_context.feed(RpmTransactionTasks())
    current_actor_context.run()

    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert 'rhui-azure-rhel8' in result[0].to_upgrade
