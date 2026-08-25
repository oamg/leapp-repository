from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround, TargetUserSpaceInfo

OL_SWAP_SCRIPT_NAME = 'swaporaclepackages'


def process():
    if get_source_distro_id() != 'ol' or get_target_distro_id() != 'rhel':
        return

    # Consuming TargetUserSpaceInfo guarantees this actor runs after the target
    # userspace has been created; without it there is nothing to swap against.
    if not next(api.consume(TargetUserSpaceInfo), None):
        return

    api.produce(
        DNFWorkaround(
            display_name='Swap Oracle Linux packages',
            script_path=api.current_actor().get_common_tool_path(OL_SWAP_SCRIPT_NAME),
        )
    )
