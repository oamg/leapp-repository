from leapp.models import (
    InstalledRedHatSignedRPM,
    RepositoriesFacts,
    RepositoryData,
    RepositoryFile,
    RPM,
    UsedRepositories
)
from leapp.snactor.fixture import current_actor_context


def get_sample_rpm(name, repository):
    return RPM(
        name=name,
        epoch='1',
        packager='Red Hat Inc.',
        version='0.0.1',
        release='1.el7',
        arch='x86_64',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM UTC, Key ID 0123456789abcdef',
        repository=repository)


def get_sample_installed_pkgs(pkgs):
    return InstalledRedHatSignedRPM(items=[get_sample_rpm(*p) for p in pkgs])


def get_sample_repository(repoid, name):
    return RepositoryFile(file='/etc/yum.d/sample.repo', data=[RepositoryData(
        repoid=repoid,
        name=name,
        enabled=True)])


def get_sample_repositories(repos):
    return RepositoriesFacts(
        repositories=[get_sample_repository(*r) for r in repos])


def test_actor_execution(current_actor_context):
    installed = get_sample_installed_pkgs([
        ('pkg1', 'rhel-7-server-rpms'),
        ('pkg2', 'rhel-7-server-rpms')])

    repos = get_sample_repositories([
        ('rhel-7-server-rpms', 'RHEL 7 Server'),
        ('rhel-7-unused-rpms', 'RHEL 7 Unused')])

    current_actor_context.feed(installed)
    current_actor_context.feed(repos)
    current_actor_context.run()
    assert current_actor_context.consume(UsedRepositories)
    used_repos = current_actor_context.consume(UsedRepositories)[0].repositories
    assert len(used_repos) == 1
    assert used_repos[0].repository == 'rhel-7-server-rpms'
    assert len(used_repos[0].packages) == 2
    assert used_repos[0].packages == ['pkg1', 'pkg2']
