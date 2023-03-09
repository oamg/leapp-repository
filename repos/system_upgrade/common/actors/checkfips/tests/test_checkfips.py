import pytest

from leapp.libraries.common.config import version
from leapp.models import FIPSInfo, Report
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize(('fips_info', 'target_major_version', 'should_inhibit'), [
    (FIPSInfo(is_enabled=True), '8', True),
    (FIPSInfo(is_enabled=True), '9', False),
    (FIPSInfo(is_enabled=False), '8', False),
    (FIPSInfo(is_enabled=False), '9', False),
])
def test_check_fips(monkeypatch, current_actor_context, fips_info, target_major_version, should_inhibit):
    monkeypatch.setattr(version, 'get_target_major_version', lambda: target_major_version)
    current_actor_context.feed(fips_info)
    current_actor_context.run()
    if should_inhibit:
        output = current_actor_context.consume(Report)
        assert len(output) == 1
        assert is_inhibitor(output[0].report)
    else:
        assert not any(is_inhibitor(msg.report) for msg in current_actor_context.consume(Report))
