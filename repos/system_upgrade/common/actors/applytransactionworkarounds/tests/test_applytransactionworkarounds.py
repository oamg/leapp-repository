from leapp.libraries.actor import applytransactionworkarounds
from leapp.libraries.common import mounting
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import TargetUserSpaceInfo

_EXPECTED_BINDS = ['/:/installroot']


class MockedNspawnActions:
    """Records how NspawnActions was constructed and used as a context manager."""

    def __init__(self):
        self.init_kwargs = None
        self.entered = False
        self.exited = False

    def __call__(self, **kwargs):
        self.init_kwargs = kwargs
        return self

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        return False


class MockedApplyWorkarounds:
    """Records the arguments apply_workarounds was called with."""

    def __init__(self):
        self.called = 0
        self.args = None

    def __call__(self, *args):
        self.called += 1
        self.args = args


def test_process_applies_workarounds_in_target_userspace(monkeypatch):
    target_userspace_info = TargetUserSpaceInfo(
        path='/path/to/userspace',
        scratch='/path/to/scratch',
        mounts='/path/to/mounts',
    )
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[target_userspace_info]))
    nspawn = MockedNspawnActions()
    apply = MockedApplyWorkarounds()
    monkeypatch.setattr(mounting, 'NspawnActions', nspawn)
    monkeypatch.setattr(dnfplugin, 'apply_workarounds', apply)

    applytransactionworkarounds.process()

    # the container is built from the target userspace path with installroot bind mounted
    assert nspawn.init_kwargs == {'base_dir': target_userspace_info.path, 'binds': _EXPECTED_BINDS}
    assert nspawn.entered and nspawn.exited
    # workarounds run inside that container context, with no host context
    assert apply.called == 1
    assert apply.args == (None, nspawn)
