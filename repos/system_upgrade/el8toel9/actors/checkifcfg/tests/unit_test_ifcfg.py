import mock
import six

from leapp import reporting
from leapp.libraries.actor import checkifcfg_ifcfg as ifcfg
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RPM, RpmTransactionTasks

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

NETWORK_SCRIPTS_RPM = RPM(
    name='network-scripts', version='10.00.17', release='1.el8', epoch='',
    packager=RH_PACKAGER, arch='x86_64',
    pgpsig='RSA/SHA256, Fri 04 Feb 2022 03:32:47 PM CET, Key ID 199e2f91fd431d51'
)

NETWORK_MANAGER_RPM = RPM(
    name='NetworkManager', version='1.36.0', release='0.8.el8', epoch='1',
    packager=RH_PACKAGER, arch='x86_64',
    pgpsig='RSA/SHA256, Mon 14 Feb 2022 08:45:37 PM CET, Key ID 199e2f91fd431d51'
)

INITSCRIPTS_INSTALLED = CurrentActorMocked(
    msgs=[InstalledRPM(items=[NETWORK_SCRIPTS_RPM])]
)

INITSCRIPTS_AND_NM_INSTALLED = CurrentActorMocked(
    msgs=[InstalledRPM(items=[NETWORK_SCRIPTS_RPM, NETWORK_MANAGER_RPM])]
)


def test_ifcfg_none(monkeypatch):
    """
    No report and don't install anything if there are no ifcfg files.
    """

    monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_AND_NM_INSTALLED)
    monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
    monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('hello', 'world',))
    monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    ifcfg.process()
    assert not reporting.create_report.called
    assert not api.produce.called


def test_ifcfg_rule_file(monkeypatch):
    """
    Install NetworkManager-dispatcher-routing-rules package if there's a
    file with ip rules.
    """

    monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_AND_NM_INSTALLED)
    monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
    monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('hello', 'world', 'rule-eth0',))
    monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    ifcfg.process()
    assert not reporting.create_report.called
    assert api.produce.called
    assert isinstance(api.produce.model_instances[0], RpmTransactionTasks)
    assert api.produce.model_instances[0].to_install == ['NetworkManager-dispatcher-routing-rules']


def test_ifcfg_good_type(monkeypatch):
    """
    No report if there's an ifcfg file that would work with NetworkManager.
    Make sure NetworkManager itself is installed though.
    """

    mock_config = mock.mock_open(read_data="TYPE=Ethernet")
    with mock.patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config) as mock_ifcfg:
        monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_AND_NM_INSTALLED)
        monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
        monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('hello', 'world', 'ifcfg-eth0', 'ifcfg-lo',))
        monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
        monkeypatch.setattr(reporting, "create_report", create_report_mocked())
        ifcfg.process()
        mock_ifcfg.assert_called_once_with('/etc/sysconfig/network-scripts/ifcfg-eth0')
        assert not reporting.create_report.called
        assert api.produce.called
        assert isinstance(api.produce.model_instances[0], RpmTransactionTasks)
        assert api.produce.model_instances[0].to_install == ['NetworkManager']


def test_ifcfg_not_controlled(monkeypatch):
    """
    Report if there's a NM_CONTROLLED=no file.
    """

    mock_config = mock.mock_open(read_data="TYPE=Ethernet\nNM_CONTROLLED=no")
    with mock.patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config) as mock_ifcfg:
        monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_INSTALLED)
        monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
        monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('hello', 'world', 'ifcfg-eth0',))
        monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
        monkeypatch.setattr(reporting, "create_report", create_report_mocked())
        ifcfg.process()
        mock_ifcfg.assert_called_once_with('/etc/sysconfig/network-scripts/ifcfg-eth0')
        assert reporting.create_report.called
        assert 'disabled NetworkManager' in reporting.create_report.report_fields['title']
        assert api.produce.called


def test_ifcfg_unknown_type(monkeypatch):
    """
    Report if there's configuration for a type we don't recognize.
    """

    mock_config = mock.mock_open(read_data="TYPE=AvianCarrier")
    with mock.patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config) as mock_ifcfg:
        monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_AND_NM_INSTALLED)
        monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
        monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('hello', 'world', 'ifcfg-pigeon0',))
        monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
        monkeypatch.setattr(reporting, "create_report", create_report_mocked())
        ifcfg.process()
        mock_ifcfg.assert_called_once_with('/etc/sysconfig/network-scripts/ifcfg-pigeon0')
        assert reporting.create_report.called
        assert 'unsupported device types' in reporting.create_report.report_fields['title']
        assert not api.produce.called


def test_ifcfg_install_subpackage(monkeypatch):
    """
    Install NetworkManager-team if there's a team connection and also
    ensure NetworkManager-config-server is installed if NetworkManager
    was not there.
    """

    mock_config = mock.mock_open(read_data="TYPE=Team")
    with mock.patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config) as mock_ifcfg:
        monkeypatch.setattr(ifcfg.api, 'current_actor', INITSCRIPTS_INSTALLED)
        monkeypatch.setattr(ifcfg.api, "produce", produce_mocked())
        monkeypatch.setattr(ifcfg.os, 'listdir', lambda dummy: ('ifcfg-team0',))
        monkeypatch.setattr(ifcfg.os.path, 'isfile', lambda dummy: True)
        monkeypatch.setattr(reporting, "create_report", create_report_mocked())
        ifcfg.process()
        mock_ifcfg.assert_called_once_with('/etc/sysconfig/network-scripts/ifcfg-team0')
        assert not reporting.create_report.called
        assert api.produce.called
        assert isinstance(api.produce.model_instances[0], RpmTransactionTasks)
        assert api.produce.model_instances[0].to_install == [
            'NetworkManager-team',
            'NetworkManager-config-server'
        ]
