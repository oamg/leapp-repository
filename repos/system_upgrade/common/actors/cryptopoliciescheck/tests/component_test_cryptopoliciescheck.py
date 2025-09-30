import pytest

from leapp.libraries.common.config import version
from leapp.models import (
    CopyFile,
    CryptoPolicyInfo,
    CustomCryptoPolicy,
    CustomCryptoPolicyModule,
    Report,
    TargetUserSpacePreupgradeTasks
)


@pytest.mark.parametrize(('source_version'), [
    ('8'),
    ('9'),
])
def test_actor_execution_default(monkeypatch, current_actor_context, source_version):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_version)
    current_actor_context.feed(
        CryptoPolicyInfo(
            current_policy="DEFAULT",
            custom_policies=[],
            custom_modules=[],
        )
    )
    current_actor_context.run()
    assert not current_actor_context.consume(TargetUserSpacePreupgradeTasks)


@pytest.mark.parametrize(('source_version', 'should_run'), [
    ('8', True),
    ('9', True),
])
def test_actor_execution_legacy(monkeypatch, current_actor_context, source_version, should_run):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_version)
    current_actor_context.feed(
        CryptoPolicyInfo(
            current_policy="LEGACY",
            custom_policies=[],
            custom_modules=[],
        )
    )
    current_actor_context.run()

    if should_run:
        assert current_actor_context.consume(TargetUserSpacePreupgradeTasks)
        u = current_actor_context.consume(TargetUserSpacePreupgradeTasks)[0]
        assert u.install_rpms == ['crypto-policies-scripts']
        assert u.copy_files == []

        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(TargetUserSpacePreupgradeTasks)


@pytest.mark.parametrize(('source_version', 'should_run'), [
    ('8', True),
    ('9', True),
])
def test_actor_execution_custom(monkeypatch, current_actor_context, source_version, should_run):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_version)
    current_actor_context.feed(
        CryptoPolicyInfo(
            current_policy="CUSTOM:SHA2",
            custom_policies=[
                CustomCryptoPolicy(name='CUSTOM', path='/etc/crypto-policies/policies/CUSTOM.pol'),
            ],
            custom_modules=[
                CustomCryptoPolicyModule(name='SHA2', path='/etc/crypto-policies/policies/modules/SHA2.pmod'),
            ],
        )
    )
    current_actor_context.run()

    if should_run:
        assert current_actor_context.consume(TargetUserSpacePreupgradeTasks)
        u = current_actor_context.consume(TargetUserSpacePreupgradeTasks)[0]
        assert u.install_rpms == ['crypto-policies-scripts']
        assert u.copy_files == [
            CopyFile(src='/etc/crypto-policies/policies/CUSTOM.pol'),
            CopyFile(src='/etc/crypto-policies/policies/modules/SHA2.pmod'),
        ]

        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(TargetUserSpacePreupgradeTasks)
