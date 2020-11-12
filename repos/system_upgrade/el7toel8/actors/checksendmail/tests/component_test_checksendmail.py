from leapp.models import (
    DaemonList,
    InstalledRedHatSignedRPM,
    RPM,
    SendmailMigrationDecision,
    TcpWrappersFacts,
)
from leapp.reporting import Report


RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

with_sendmail = [
    RPM(name='grep', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
    RPM(name='sendmail', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]

without_sendmail = [
    RPM(name='grep', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
    RPM(name='sed', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]


def create_modulesfacts(installed_rpm):
    return InstalledRedHatSignedRPM(items=installed_rpm)


def test_actor_without_sendmail_package(current_actor_context):
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[])
    current_actor_context.feed(create_modulesfacts(installed_rpm=without_sendmail))
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_tcp_wrappers(current_actor_context):
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[DaemonList(value=['sendmail'])])
    current_actor_context.feed(create_modulesfacts(installed_rpm=with_sendmail))
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert 'inhibitor' in report_fields['groups']
