import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import check_fips
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FIPSInfo


@pytest.mark.parametrize(
    ('fips_info', 'sys_fips_enabled_contents', 'should_prevent_ipu'),
    (
        (FIPSInfo(is_enabled=False), '0', False),
        (FIPSInfo(is_enabled=True), '0', True),
        (FIPSInfo(is_enabled=True), '1', False),
    )
)
def test_ipu_prevention_if_fips_not_perserved(monkeypatch,
                                              fips_info,
                                              sys_fips_enabled_contents,
                                              should_prevent_ipu):

    mocked_actor = CurrentActorMocked(msgs=[fips_info])
    monkeypatch.setattr(check_fips, 'read_sys_fips_state', lambda: sys_fips_enabled_contents)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    if should_prevent_ipu:
        with pytest.raises(StopActorExecutionError):
            check_fips.check_fips_state_perserved()
    else:
        check_fips.check_fips_state_perserved()  # unhandled exception with crash the test
