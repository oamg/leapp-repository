import os

import pytest

from leapp.libraries.actor import scankrb5conf
from leapp.libraries.actor.scankrb5conf import fetch_outdated_krb5_conf_files
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    'inp,exp_out',
    [
        (['files/krb5conf_outdated'], ['files/krb5conf_outdated']),
        (['files/krb5conf_not_affected'], []),
        (['files/krb5conf_not_configured'], []),
        (['files/krb5conf_uptodate'], []),
        (['files'], ['files/krb5conf_outdated']),
    ],
)
def test_fetch_outdated_krb5_conf_files_with_files(inp, exp_out):
    msg = fetch_outdated_krb5_conf_files([os.path.join(CUR_DIR, i) for i in inp])
    assert len(msg.unmanaged_files) == len(exp_out)
    assert set(msg.unmanaged_files) == set(os.path.join(CUR_DIR, o) for o in exp_out)


def test_fetch_outdated_krb5_conf_files_rpm_provided(monkeypatch):
    """Test that rpm_provided_files is populated when file belongs to an RPM not in DistributionSignedRPM."""
    test_rpm_name = 'krb5-libs'
    test_file_path = os.path.join(CUR_DIR, 'files/krb5conf_outdated')

    def mock_run(cmd, split=False):
        assert cmd == ['/usr/bin/rpm', '-qf', test_file_path]
        return {'stdout': [test_rpm_name]}

    monkeypatch.setattr(scankrb5conf, 'run', mock_run)

    other_rpm = RPM(name='other-package', epoch='0', version='1.0', release='1.el9',
                    arch='x86_64', packager='Red Hat', pgpsig='RSA/SHA256')
    dist_signed_rpms = DistributionSignedRPM(items=[other_rpm])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[dist_signed_rpms]))

    msg = fetch_outdated_krb5_conf_files([test_file_path])

    # File should be in rpm_provided_files since the owning RPM is not in DistributionSignedRPM
    assert len(msg.rpm_provided_files) == 1
    assert msg.rpm_provided_files[0].path == test_file_path
    assert msg.rpm_provided_files[0].rpm == test_rpm_name
    # Should not be in unmanaged_files
    assert len(msg.unmanaged_files) == 0
