import pytest

from leapp.libraries.common.config import version
from leapp.models import DracutModule, FIPSInfo, Report, UpgradeInitramfsTasks
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize(('fips_info', 'target_major_version', 'should_produce'), [
    (FIPSInfo(is_enabled=False), '9', False),
    (FIPSInfo(is_enabled=True), '9', True),
    (FIPSInfo(is_enabled=False), '10', False),
    (FIPSInfo(is_enabled=True), '10', False),
])
def test_check_fips(monkeypatch, current_actor_context, fips_info, target_major_version, should_produce):
    monkeypatch.setattr(version, 'get_target_major_version', lambda: target_major_version)

    current_actor_context.feed(fips_info)
    current_actor_context.run()

    # no inhibitor in any case
    assert not any(is_inhibitor(msg.report) for msg in current_actor_context.consume(Report))

    output = current_actor_context.consume(UpgradeInitramfsTasks)
    if should_produce:
        assert len(output) == 1

        expected_initramfs_files = [
            '/etc/crypto-policies/back-ends/opensslcnf.config',
            '/etc/pki/tls/openssl.cnf',
            '/usr/lib64/ossl-modules/fips.so',
        ]

        assert output[0].include_files == expected_initramfs_files

        assert len(output[0].include_dracut_modules) == 1
        mod = output[0].include_dracut_modules[0]
        assert isinstance(mod, DracutModule)
        assert mod.name == "fips"
    else:
        assert not output
