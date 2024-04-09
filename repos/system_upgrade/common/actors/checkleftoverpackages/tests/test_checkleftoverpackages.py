import pytest

from leapp.libraries.actor import checkleftoverpackages
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledUnsignedRPM, LeftoverPackages, RPM


@pytest.mark.parametrize(
    ('source_major_version', 'rpm_name', 'release', 'expected_to_be_removed'),
    (
        (7, 'sed', '7.el7', True),
        (8, 'sed', '8.el7', True),
        (7, 'gnutls', '8.el8_9.1', False),
        (7, 'unsigned', '1.el7', False),

        (7, 'leapp', '1.el7', False),
        (8, 'leapp-upgrade-el8toel9', '1.el8', False),
        (8, 'leapp-upgrade-el8toel9-deps', '1.el8', False),
    )
)
def test_package_to_be_removed(monkeypatch, source_major_version, rpm_name, release, expected_to_be_removed):
    rpm_details = {
        'version': '0.1',
        'epoch': '0',
        'packager': 'packager',
        'arch': 'noarch',
        'pgpsig': 'sig'
    }

    def get_installed_rpms_mocked():
        return ['{name}|{version}|{release}|{epoch}|{packager}|{arch}|{pgpsig}'.format(
            name=rpm_name,
            version=rpm_details['version'],
            release=release,
            epoch=rpm_details['epoch'],


            packager=rpm_details['packager'],
            arch=rpm_details['arch'],
            pgpsig=rpm_details['pgpsig']
        )]

    UnsignedRPM = RPM(name='unsigned', version='0.1', release=release, epoch='0',
                      packager='packager', arch='noarch', pgpsig='OTHER_SIG')

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[InstalledUnsignedRPM(items=[UnsignedRPM])]))
    monkeypatch.setattr(checkleftoverpackages, 'get_installed_rpms', get_installed_rpms_mocked)
    monkeypatch.setattr(checkleftoverpackages, 'get_source_major_version', lambda: str(source_major_version))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkleftoverpackages.process()

    expected_output = LeftoverPackages()
    if expected_to_be_removed:
        expected_output.items.append(RPM(name=rpm_name, release=release, **rpm_details))

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert api.produce.model_instances[0] == expected_output
