import contextlib
import functools
import os
import re
import time

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import CalledProcessError, api
from leapp.models import RHSMInfo

_RE_REPO_UID = re.compile(r'Repo ID:\s*([^\s]+)')
_RE_RELEASE = re.compile(r'Release:\s*([^\s]+)')
_RE_SKU_CONSUMED = re.compile(r'SKU:\s*([^\s]+)')
_ATTEMPTS = 5
_RETRY_SLEEP = 5
_DEFAULT_RHSM_REPOFILE = '/etc/yum.repos.d/redhat.repo'


def _rhsm_retry(max_attempts, sleep=None):
    """
    A decorator to retry executing a function/method if unsuccessful.

    The function/method execution is considered unsuccessful when it raises StopActorExecutionError.

    :param max_attempts: Maximum number of attempts to execute the decorated function/method.
    :param sleep: Time to wait between attempts. In seconds.
    """
    def impl(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            attempts = 0
            while True:
                attempts += 1
                try:
                    return f(*args, **kwargs)
                except StopActorExecutionError:
                    if max_attempts <= attempts:
                        api.current_logger().warning(
                            'Attempt %d of %d to perform %s failed. Maximum number of retries has been reached.',
                            attempts, max_attempts, f.__name__)
                        raise
                    if sleep:
                        api.current_logger().info(
                            'Attempt %d of %d to perform %s failed - Retrying after %s seconds',
                            attempts, max_attempts, f.__name__, str(sleep))
                        time.sleep(sleep)
                    else:
                        api.current_logger().info(
                            'Attempt %d of %d to perform %s failed - Retrying...', attempts, max_attempts, f.__name__)
        return wrapper
    return impl


@contextlib.contextmanager
def _handle_rhsm_exceptions(hint=None):
    """
    Context manager based function that handles exceptions of `run` for the subscription-manager calls.
    """
    try:
        yield
    except OSError as e:
        api.current_logger().error('Failed to execute subscription-manager executable')
        raise StopActorExecutionError(
            message='Unable to execute subscription-manager executable: {}'.format(str(e)),
            details={
                'hint': 'Please ensure subscription-manager is installed and executable.'
            }
        )
    except CalledProcessError as e:
        _def_hint = (
            'Please ensure you have a valid RHEL subscription and your network is up.'
            ' If you are using proxy for Red Hat subscription-manager, please make sure'
            ' it is specified inside the /etc/rhsm/rhsm.conf file.'
            ' Or use the --no-rhsm option when running leapp, if you do not want to'
            ' use subscription-manager for the in-place upgrade and you want to'
            ' deliver all target repositories by yourself or using RHUI on public cloud.'
        )
        raise StopActorExecutionError(
            message='A subscription-manager command failed to execute',
            details={
                'details': str(e),
                'stderr': e.stderr,
                'hint': hint or _def_hint
            }
        )


def skip_rhsm():
    """Check whether we should skip RHSM related code."""
    return get_env('LEAPP_NO_RHSM', '0') == '1'


def with_rhsm(f):
    """Decorator to allow skipping RHSM functions by executing a no-op."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not skip_rhsm():
            return f(*args, **kwargs)
        return None
    return wrapper


@with_rhsm
def get_attached_skus(context):
    """
    Retrieve the list of the SKUs the system is attached to with the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: SKUs the current system is attached to.
    :rtype: List(string)
    """
    with _handle_rhsm_exceptions():
        result = context.call(['subscription-manager', 'list', '--consumed'], split=False)
        return _RE_SKU_CONSUMED.findall(result['stdout'])


def get_available_repo_ids(context):
    """
    Retrieve repo ids of all the repositories available through the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: Repositories that are available to the current system through the subscription-manager
    :rtype: List(string)
    """
    # Regenerated redhat.repo file ...
    # FIXME: try to come up with something less invasive than yum clean all
    # but still safe to call..
    cmd = ['yum', 'clean', 'all']
    try:
        context.call(cmd)
    except CalledProcessError as exc:
        raise StopActorExecutionError(
            'Unable to use yum successfully',
            details={'details': str(exc), 'stderr': exc.stderr}
        )

    repofiles = repofileutils.get_parsed_repofiles(context)

    # TODO: move this functionality out! Create check actor that will do
    # the inhibit. The functionality is really not good here in the current
    # shape of the leapp-repository. See the targetuserspacecreator and
    # systemfacts actor if this is moved out.
    # Issue: #486
    _inhibit_on_duplicate_repos(repofiles)
    rhsm_repos = []
    for rfile in repofiles:
        if rfile.file == _DEFAULT_RHSM_REPOFILE and rfile.data:
            rhsm_repos = [repo.repoid for repo in rfile.data]
            rhsm_repos.sort()
            break

    list_separator_fmt = '\n    - '
    if rhsm_repos:
        api.current_logger().info('The following repoids are available through RHSM:{0}{1}'
                                  .format(list_separator_fmt, list_separator_fmt.join(rhsm_repos)))
    else:
        api.current_logger().info('There are no repos available through RHSM.')
    return rhsm_repos


def _inhibit_on_duplicate_repos(repofiles):
    """
    Inhibit the upgrade if any repoid is defined multiple times.

    When that happens, it not only shows misconfigured system, but then
    we can't get details of all the available repos as well.
    """
    duplicates = repofileutils.get_duplicate_repositories(repofiles).keys()

    if not duplicates:
        return
    list_separator_fmt = '\n    - '
    api.current_logger().warning(
        'The following repoids are defined multiple times:{0}{1}'
        .format(list_separator_fmt, list_separator_fmt.join(duplicates))
    )

    reporting.create_report([
        reporting.Title('A YUM/DNF repository defined multiple times'),
        reporting.Summary(
            'The following repositories are defined multiple times:{0}{1}'
            .format(list_separator_fmt, list_separator_fmt.join(duplicates))
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.REPOSITORY, reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint='Remove the duplicate repository definitions.')
    ])


@with_rhsm
def get_enabled_repo_ids(context):
    """
    Retrieve repo ids of all the repositories enabled through the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: Repositories that are enabled on the current system through the subscription-manager.
    :rtype: List(string)
    """
    with _handle_rhsm_exceptions():
        result = context.call(['subscription-manager', 'repos', '--list-enabled'], split=False)
        return _RE_REPO_UID.findall(result['stdout'])


@with_rhsm
@_rhsm_retry(max_attempts=_ATTEMPTS, sleep=_RETRY_SLEEP)
def unset_release(context):
    """
    Unset the configured release from the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'release', '--unset'], split=False)


@with_rhsm
@_rhsm_retry(max_attempts=_ATTEMPTS, sleep=_RETRY_SLEEP)
def set_release(context, release):
    """
    Set the release (RHEL minor version) through the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param release: Release to set the subscription-manager to.
    :type release: str
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'release', '--set', release], split=False)


@with_rhsm
def get_release(context):
    """
    Retrieves the release the subscription-manager has been pinned to, if applicable.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: Release the subscription-manager is set to.
    :rtype: string
    """
    with _handle_rhsm_exceptions():
        result = context.call(['subscription-manager', 'release'], split=False)
        result = _RE_RELEASE.findall(result['stdout'])
        return result[0] if result else ''


@with_rhsm
@_rhsm_retry(max_attempts=_ATTEMPTS, sleep=_RETRY_SLEEP)
def refresh(context):
    """
    Calls 'subscription-manager refresh'

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'refresh'], split=False)


@with_rhsm
def get_existing_product_certificates(context):
    """
    Retrieves information about existing product certificates on the system.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: Paths to product certificates that are currently installed on the system.
    :rtype: List(string)
    """
    certs = []
    for path in ('/etc/pki/product', '/etc/pki/product-default'):
        if not os.path.isdir(context.full_path(path)):
            continue
        curr_certs = [os.path.join(path, f) for f in os.listdir(context.full_path(path))
                      if os.path.isfile(os.path.join(context.full_path(path), f))]
        if curr_certs:
            certs.extend(curr_certs)
    return certs


# DO NOT SET the with_rhsm decorator for this function
def set_container_mode(context):
    """
    Put RHSM into the container mode.

    Inside the container, we have to ensure the RHSM is not used AND that host
    is not affected. If the RHSM is not set into the container mode, the host
    could be affected and the generated repo file in the container could be
    affected as well (e.g. when the release is set, using rhsm, on the host).

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    """
    if not context.is_isolated():
        api.current_logger().error('Trying to set RHSM into the container mode'
                                   'on host. Skipping the action.')
        return
    try:
        context.call(['ln', '-s', '/etc/rhsm', '/etc/rhsm-host'])
    except CalledProcessError:
        raise StopActorExecutionError(
                message='Cannot set the container mode for the subscription-manager.')


@with_rhsm
def switch_certificate(context, rhsm_info, cert_path):
    """
    Perform all actions needed to switch the passed RHSM product certificate.

    This function will copy the certificate to /etc/pki/product, and /etc/pki/product-default if necessary, and
    remove other product certificates from there.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of the RHSMInfo model
    :type rhsm_info: RHSMInfo model
    :param cert_path: Path to the product certificate to switch to
    :type cert_path: string
    """
    for existing in rhsm_info.existing_product_certificates:
        try:
            context.remove(existing)
        except OSError:
            api.current_logger().warning('Failed to remove existing certificate: %s', existing, exc_info=True)

    for path in ('/etc/pki/product', '/etc/pki/product-default'):
        if os.path.isdir(context.full_path(path)):
            context.copy_to(cert_path, os.path.join(path, os.path.basename(cert_path)))


@with_rhsm
def scan_rhsm_info(context):
    """
    Gather all the RHSM information of the source system.

    It's not intended for gathering RHSM info about the target system within a container.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: An instance of an RHSMInfo model.
    :rtype: RHSMInfo model
    """
    info = RHSMInfo()
    info.attached_skus = get_attached_skus(context)
    info.available_repos = get_available_repo_ids(context)
    info.enabled_repos = get_enabled_repo_ids(context)
    info.release = get_release(context)
    info.existing_product_certificates.extend(get_existing_product_certificates(context))
    return info
