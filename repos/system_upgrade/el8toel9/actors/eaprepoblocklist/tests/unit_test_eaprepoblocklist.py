from leapp.libraries.actor import eaprepoblocklist
from leapp.models import DistributionSignedRPM, RepositoriesSetupTasks, RPM
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'
RH_PGPSIG = 'RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'


def make_rpm(name, version):
    return RPM(
        name=name,
        version=version,
        release='1.el8',
        epoch='0',
        arch='noarch',
        packager=RH_PACKAGER,
        pgpsig=RH_PGPSIG,
    )


EAP74_RPM = make_rpm('eap7-wildfly', '7.4.0')
EAP80_RPM = make_rpm('eap8-wildfly', '8.0.0')
EAP81_RPM = make_rpm('eap8-wildfly', '8.1.0')


def test_no_eap_installed(monkeypatch, current_actor_context):
    monkeypatch.setattr(eaprepoblocklist, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(eaprepoblocklist, 'get_target_distro_id', lambda: 'rhel')

    current_actor_context.feed(DistributionSignedRPM(items=[]))
    current_actor_context.run()

    assert not current_actor_context.consume(RepositoriesSetupTasks)
    assert not current_actor_context.consume(Report)


def test_eap74_installed(monkeypatch, current_actor_context):
    monkeypatch.setattr(eaprepoblocklist, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(eaprepoblocklist, 'get_target_distro_id', lambda: 'rhel')

    current_actor_context.feed(DistributionSignedRPM(items=[EAP74_RPM]))
    current_actor_context.run()

    tasks = current_actor_context.consume(RepositoriesSetupTasks)
    assert tasks
    task = tasks[0]
    assert 'jb-eap-7.4-for-rhel-9-x86_64-rpms' in task.to_enable
    assert 'jb-eap-7.4-els-for-rhel-9-x86_64-rpms' in task.to_enable
    assert 'jb-eap-8.0-for-rhel-9-x86_64-rpms' in task.to_block
    assert 'jb-eap-8.1-for-rhel-9-x86_64-rpms' in task.to_block
    assert not current_actor_context.consume(Report)


def test_eap80_installed(monkeypatch, current_actor_context):
    monkeypatch.setattr(eaprepoblocklist, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(eaprepoblocklist, 'get_target_distro_id', lambda: 'rhel')

    current_actor_context.feed(DistributionSignedRPM(items=[EAP80_RPM]))
    current_actor_context.run()

    reports = current_actor_context.consume(Report)
    assert reports
    assert is_inhibitor(reports[0].report)
    assert not current_actor_context.consume(RepositoriesSetupTasks)


def test_eap81_installed(monkeypatch, current_actor_context):
    monkeypatch.setattr(eaprepoblocklist, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(eaprepoblocklist, 'get_target_distro_id', lambda: 'rhel')

    current_actor_context.feed(DistributionSignedRPM(items=[EAP81_RPM]))
    current_actor_context.run()

    tasks = current_actor_context.consume(RepositoriesSetupTasks)
    assert tasks
    task = tasks[0]
    assert 'jb-eap-8.1-for-rhel-9-x86_64-rpms' in task.to_enable
    assert 'jb-eap-7.4-for-rhel-9-x86_64-rpms' in task.to_block
    assert 'jb-eap-7.4-els-for-rhel-9-x86_64-rpms' in task.to_block
    assert 'jb-eap-8.0-for-rhel-9-x86_64-rpms' in task.to_block
    assert not current_actor_context.consume(Report)


def test_non_rhel_distro(monkeypatch, current_actor_context):
    monkeypatch.setattr(eaprepoblocklist, 'get_source_distro_id', lambda: 'centos')
    monkeypatch.setattr(eaprepoblocklist, 'get_target_distro_id', lambda: 'rhel')

    current_actor_context.feed(DistributionSignedRPM(items=[EAP81_RPM]))
    current_actor_context.run()

    assert not current_actor_context.consume(RepositoriesSetupTasks)
    assert not current_actor_context.consume(Report)
