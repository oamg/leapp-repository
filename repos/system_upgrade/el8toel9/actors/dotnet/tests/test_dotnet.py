import pytest

from leapp.models import InstalledRedHatSignedRPM, Report, RPM


def _generate_rpm_with_name(name):
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


@pytest.mark.parametrize('unsupported_versions', [
    ([]),          # No unsupported versions
    ([2.1]),       # Single unsupported version
    ([3.0]),       # Other unsupported version
    ([2.1, 3.0]),  # Multiple unsupported versions
])
def test_actor_execution(monkeypatch, current_actor_context, unsupported_versions):
    """
    Install one or more dotnet-runtime packages for unsupported versions
    and verify a report is generated.
    """

    # Couple of random packages
    rpms = [_generate_rpm_with_name('sed'),
            _generate_rpm_with_name('htop')]

    # dotnet-runtime-{version} packages
    for version in unsupported_versions:
        rpms += [_generate_rpm_with_name(f'dotnet-runtime-{version}')]

    # Executed actor feeded with fake RPMs
    current_actor_context.feed(InstalledRedHatSignedRPM(items=rpms))
    current_actor_context.run()

    if unsupported_versions:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
