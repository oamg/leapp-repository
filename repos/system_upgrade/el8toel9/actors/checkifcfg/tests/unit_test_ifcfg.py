from leapp.models import IfCfg, IfCfgProperty, InstalledRPM, RPM, RpmTransactionTasks
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor

RH_PACKAGER = "Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>"

NETWORK_SCRIPTS_RPM = RPM(
    name="network-scripts",
    version="10.00.17",
    release="1.el8",
    epoch="",
    packager=RH_PACKAGER,
    arch="x86_64",
    pgpsig="RSA/SHA256, Fri 04 Feb 2022 03:32:47 PM CET, Key ID 199e2f91fd431d51",
)

NETWORK_MANAGER_RPM = RPM(
    name="NetworkManager",
    version="1.36.0",
    release="0.8.el8",
    epoch="1",
    packager=RH_PACKAGER,
    arch="x86_64",
    pgpsig="RSA/SHA256, Mon 14 Feb 2022 08:45:37 PM CET, Key ID 199e2f91fd431d51",
)

INITSCRIPTS_INSTALLED = InstalledRPM(items=[
    NETWORK_SCRIPTS_RPM
])
INITSCRIPTS_AND_NM_INSTALLED = InstalledRPM(items=[
    NETWORK_SCRIPTS_RPM,
    NETWORK_MANAGER_RPM
])


def test_ifcfg_none(current_actor_context):
    """
    No report and don't install anything if there are no ifcfg files.
    """

    current_actor_context.feed(INITSCRIPTS_AND_NM_INSTALLED)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
    assert not current_actor_context.consume(RpmTransactionTasks)


def test_ifcfg_rule_file(current_actor_context):
    """
    Install NetworkManager-dispatcher-routing-rules package if there's a
    file with ip rules.
    """

    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-eth0",
        properties=(IfCfgProperty(name="TYPE", value="Ethernet"),),
        rules=("foo bar baz",),
    ))
    current_actor_context.feed(INITSCRIPTS_AND_NM_INSTALLED)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
    assert len(current_actor_context.consume(RpmTransactionTasks)) == 1
    rpm_transaction = current_actor_context.consume(RpmTransactionTasks)[0]
    assert rpm_transaction.to_install == ["NetworkManager-dispatcher-routing-rules"]


def test_ifcfg_good_type(current_actor_context):
    """
    No report if there's an ifcfg file that would work with NetworkManager.
    Make sure NetworkManager itself is installed though.
    """

    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-lo",
        properties=()
    ))
    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-eth0",
        properties=(IfCfgProperty(name="TYPE", value="Ethernet"),)
    ))
    current_actor_context.feed(INITSCRIPTS_AND_NM_INSTALLED)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
    assert len(current_actor_context.consume(RpmTransactionTasks)) == 1
    rpm_transaction = current_actor_context.consume(RpmTransactionTasks)[0]
    assert rpm_transaction.to_install == ["NetworkManager"]


def test_ifcfg_not_controlled(current_actor_context):
    """
    Report if there's a NM_CONTROLLED=no file.
    """

    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-eth0",
        properties=(
            IfCfgProperty(name="TYPE", value="Ethernet"),
            IfCfgProperty(name="NM_CONTROLLED", value="no"),
        )
    ))
    current_actor_context.feed(INITSCRIPTS_INSTALLED)
    current_actor_context.run()
    assert len(current_actor_context.consume(Report)) == 1
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert "disabled NetworkManager" in report_fields['title']


def test_ifcfg_unknown_type(current_actor_context):
    """
    Report if there's configuration for a type we don't recognize.
    """

    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-pigeon0",
        properties=(IfCfgProperty(name="TYPE", value="AvianCarrier"),)
    ))
    current_actor_context.feed(INITSCRIPTS_AND_NM_INSTALLED)
    current_actor_context.run()
    assert len(current_actor_context.consume(Report)) == 1
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert "unsupported device types" in report_fields['title']


def test_ifcfg_install_subpackage(current_actor_context):
    """
    Install NetworkManager-team if there's a team connection and also
    ensure NetworkManager-config-server is installed if NetworkManager
    was not there.
    """

    current_actor_context.feed(IfCfg(
        filename="/NM/ifcfg-team0",
        properties=(IfCfgProperty(name="TYPE", value="Team"),)
    ))
    current_actor_context.feed(INITSCRIPTS_INSTALLED)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
    assert len(current_actor_context.consume(RpmTransactionTasks)) == 1
    rpm_transaction = current_actor_context.consume(RpmTransactionTasks)[0]
    assert rpm_transaction.to_install == [
        "NetworkManager-team",
        "NetworkManager-config-server",
    ]
