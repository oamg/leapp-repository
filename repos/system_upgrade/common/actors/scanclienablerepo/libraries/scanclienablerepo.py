from leapp.libraries.common import config
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository


def process():
    if not config.get_env('LEAPP_ENABLE_REPOS'):
        return
    api.current_logger().info('The --enablerepo option has been used,')
    for repoid in config.get_env('LEAPP_ENABLE_REPOS').split(','):
        api.produce(CustomTargetRepository(repoid=repoid))
