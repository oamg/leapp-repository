from leapp.libraries.common.config import get_source_distro_id
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround


def process():
    if get_source_distro_id() != 'rocky':
        return

    api.produce(
        DNFWorkaround(
            display_name='Rocky Linux compatibility symlinks fix',
            script_path=api.current_actor().get_common_tool_path('removerockylogossymlinks'),
        )
    )
