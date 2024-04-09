import pytest

from leapp.libraries.actor import removeleftoverpackages
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import LeftoverPackages, RemovedPackages, RPM


def test_get_leftover_packages(monkeypatch):
    rpm = RPM(name='rpm', version='1.0', release='1.el7', epoch='0', packager='foo', arch='noarch', pgpsig='SIG')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[LeftoverPackages(items=[rpm])]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    assert removeleftoverpackages._get_leftover_packages() == LeftoverPackages(items=[rpm])


def test_no_leftover_packages(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[LeftoverPackages()]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    packages = removeleftoverpackages._get_leftover_packages()
    assert packages is None
    assert api.current_logger.infomsg == ['No leftover packages, skipping...']


def test_remove_leftover_packages_error(monkeypatch):
    def get_leftover_pkgs():
        return LeftoverPackages(items=[RPM(name='rpm', version='1.0', release='1.el7', epoch='0',
                                           packager='packager', arch='noarch', pgpsig='SIG')])

    def mocked_run(cmd):
        raise CalledProcessError(command=cmd,
                                 message='mocked error',
                                 result={'stdout': 'out', 'stderr': 'err', 'exit_code': 1, 'signal': 0})

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(removeleftoverpackages, '_get_leftover_packages', get_leftover_pkgs)
    monkeypatch.setattr(removeleftoverpackages, 'get_installed_rpms', lambda: [])
    monkeypatch.setattr(removeleftoverpackages, 'skip_rhsm', lambda: False)
    monkeypatch.setattr(removeleftoverpackages, 'run', mocked_run)

    removeleftoverpackages.process()

    assert api.produce.called == 0
    assert api.current_logger.errmsg == ['Failed to remove packages: rpm-1.0-1.el7']


@pytest.mark.parametrize(
    ('installed_rpms'),
    (
        ([]),
        (['rpm1']),
        (['rpm1', 'rpm2']),
    )
)
def test_get_removed_packages(monkeypatch, installed_rpms):
    rpm_details = {
        'version': '1.0',
        'release': '1.el7',
        'epoch': '0',
        'packager': 'packager',
        'arch': 'noarch',
        'pgpsig': 'SIG'
    }
    rpm_details_composed = '|'.join([rpm_details[key] for key in ['version', 'release', 'epoch',
                                                                  'packager', 'arch', 'pgpsig']])
    mocked_installed_rpms = ['{}|{}'.format(rpm, rpm_details_composed) for rpm in installed_rpms]

    monkeypatch.setattr(removeleftoverpackages, 'get_installed_rpms', lambda: [])

    removed_packages = removeleftoverpackages._get_removed_packages(mocked_installed_rpms)
    removed_packages.items = sorted(removed_packages.items, key=lambda x: x.name)
    expected_output = [RPM(name=rpm, **rpm_details) for rpm in installed_rpms]
    expected_output = sorted(expected_output, key=lambda x: x.name)

    assert removed_packages == RemovedPackages(items=expected_output)


@pytest.mark.parametrize(
    ('removed_packages', 'skip_rhsm'),
    (
        ([], True),
        ([], False),
        (['rpm1'], True),
        (['rpm1', 'rpm2'], True),
        (['rpm1', 'rpm2'], False),
    )
)
def test_process(monkeypatch, removed_packages, skip_rhsm):
    pkgs = [RPM(name=pkg, version='1.0', release='1.el7', epoch='0',
                packager='packager', arch='noarch', pgpsig='SIG')
            for pkg in removed_packages]

    removed_pkgs = RemovedPackages(items=pkgs)

    def mocked_run(cmd):
        pkgs_joined = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in pkgs]
        expected_cmd = ['dnf', 'remove', '-y', '--noautoremove']
        expected_cmd += pkgs_joined

        if skip_rhsm:
            expected_cmd += ['--disableplugin', 'subscription-manager']

        assert cmd == expected_cmd

    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(removeleftoverpackages, 'run', mocked_run)
    monkeypatch.setattr(removeleftoverpackages, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(removeleftoverpackages, 'get_installed_rpms', lambda: [])
    monkeypatch.setattr(removeleftoverpackages, '_get_leftover_packages', lambda: LeftoverPackages(items=pkgs))
    monkeypatch.setattr(removeleftoverpackages, '_get_removed_packages', lambda _: removed_pkgs)

    removeleftoverpackages.process()

    assert api.produce.called == 1
    assert api.produce.model_instances == [removed_pkgs]
