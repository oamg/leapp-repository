from leapp.libraries.common import rhsm
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api, CalledProcessError, run


def _insights_register():
    try:
        run(['insights-client', '--register'])
        api.current_logger().info('Automatically registered into Red Hat Insights')
    except (CalledProcessError) as err:
        # TODO(mmatuska) produce post-upgrade report?
        api.current_logger().error(
            'Automatic registration into Red Hat Insights failed: {}'.format(err)
        )


def process():
    if rhsm.skip_rhsm() or get_env('LEAPP_NO_INSIGHTS_REGISTER', '0') == '1':
        api.current_logger().debug(
            'Skipping registration into Insights due to --no-insights-register'
            ' or LEAPP_NO_INSIGHTS_REGISTER=1 set'
        )
        return

    _insights_register()
