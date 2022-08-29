import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import CryptoPolicyInfo, TargetUserSpaceInfo

UCP_SCRIPT_PATH = '/usr/bin/update-crypto-policies'


def _set_crypto_policy(context, current_policy):
    if not os.path.exists(context.full_path(UCP_SCRIPT_PATH)):
        # consider this as heavy bug in actors and user cannot do anything - just report the bug
        raise StopActorExecutionError(
            'The update-crypto-policies tool is not installed inside the {} container.'
            .format(context.full_path('/'))
        )
    try:
        # In case of custom policies, it will most likely crash
        # TODO(pstodulk): copy custom files with the crypto policies to the container first
        context.call(['update-crypto-policies', '--set', current_policy])
    except CalledProcessError as e:
        # maybe in this case we could set an inhibitor instead?
        details = {'details:': str(e), 'stderr': e.stderr}

        # NOTE(pstodulk): In case the LEGACY crypto policy is set, I expect
        # a different root cause..
        if current_policy != 'LEGACY':
            details['hint'] = (
                'Custom crypto policies are likely used on the system.'
                ' The in-place upgrade cannot handle this correctly right now.'
                ' Consider the use of crypto policies that exists on the target system'
                ' or contact the support to prioritize the work on this feature.'
            )
        raise StopActorExecutionError(
            message='Cannot set the expected crypto policies: {}'.format(current_policy),
            details=details
        )


def process():
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    if not target_userspace_info:
        # nothing to do - an error occurred in previous actors and upgrade will be inhibited
        api.current_logger().error('Missing the TargetUserSpaceInfo message. Probably it has not been created before.')
        return
    cpi = next(api.consume(CryptoPolicyInfo), None)
    if not cpi:
        # unexpected, but still better to log the error
        api.current_logger().error('Missing the CryptoPolicyInfo message. Nothing to do')
        return
    if cpi.current_policy == 'DEFAULT':
        api.current_logger().debug('The default crypto policy detected on the host system. Nothing to do.')
        return
    with mounting.NspawnActions(base_dir=target_userspace_info.path) as context:
        _set_crypto_policy(context, cpi.current_policy)
