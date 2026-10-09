from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.stdlib import api
from leapp.models import TargetUserSpaceInfo


def process():
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    if not target_userspace_info:
        raise StopActorExecutionError("Did not receive the expected TargetUserSpaceInfo message")

    # bind mount installroot so that the workaround can e.g. import gpg keys there
    bind_mounts = ['/:/installroot']
    with mounting.NspawnActions(base_dir=target_userspace_info.path, binds=bind_mounts) as context:
        dnfplugin.apply_workarounds(None, context)
