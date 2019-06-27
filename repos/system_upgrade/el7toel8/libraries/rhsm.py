import contextlib
import functools
import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import TargetRHSMInfo


_RE_REPO_UID = re.compile(r'Repo ID:\s*([^\s]+)')
_RE_RELEASE = re.compile(r'Release:\s*([^\s]+)')
_RE_SKU_CONSUMED = re.compile(r'SKU:\s*([^\s]+)')


@contextlib.contextmanager
def _handle_rhsm_exceptions(hint=None):
    """
    Context manager based function that handles exceptions of `run` for the subscription manager calls.
    """
    try:
        yield
    except OSError as e:
        api.current_logger().error('Failed to execute subscription-manager executable')
        raise StopActorExecutionError(
            message='Unable to execute subscription-manager executable. Message: {}'.format(e.message),
            details={
                'hint': 'Please ensure subscription-manager is installed and exceutable.'
            }
        )
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='A subscription-manager command failed to execute',
            details={
                'hint': hint or 'Please ensure you have a valid RHEL subscription and your network is up.'
            }
        )


def skip_rhsm():
    """ Function to check whether we should skip RHSM related code """
    return os.getenv('LEAPP_DEVEL_SKIP_RHSM', '0') == '1'


def with_rhsm(f):
    """ Decorator to allow skipping RHSM functions by executing a no-op """
    if skip_rhsm():
        @functools.wraps(f)
        def _no_op(*args, **kwargs):
            return
        return _no_op
    return f


@with_rhsm
def get_attached_skus(context, rhsm_info):
    """
    Retrieves the list of SKU the system is attached to with the subscription manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if not rhsm_info.attached_skus:
        with _handle_rhsm_exceptions():
            result = context.call(['subscription-manager', 'list', '--consumed'], split=False)
            rhsm_info.attached_skus = _RE_SKU_CONSUMED.findall(result['stdout'])


@with_rhsm
def get_available_repo_uids(context, rhsm_info):
    """
    Retrieves all available repositories names from the subscription manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if not rhsm_info.available_repos:
        with _handle_rhsm_exceptions():
            result = context.call(['subscription-manager', 'repos'], split=False)
            rhsm_info.available_repos = _RE_REPO_UID.findall(result['stdout'])


@with_rhsm
def get_enabled_repo_uids(context, rhsm_info):
    """
    Retrieves all enabled repositories names from the subscription manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if not rhsm_info.enabled_repos:
        with _handle_rhsm_exceptions():
            result = context.call(['subscription-manager', 'repos', '--list-enabled'], split=False)
            rhsm_info.enabled_repos = _RE_REPO_UID.findall(result['stdout'])


@with_rhsm
def _get_repositories_to_use(context, rhsm_info, target_repositories):
    """
    Filters the available repositories based on the target_repositories passed.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    :param target_repositories: Instance of the TargetRepositories message.
    :type target_repositories: TargetRepositories
    :return: List of filtered repositories to use.
    :rtype: List(string)
    """
    repositories_to_use = []
    for target_repo in target_repositories:
        for rhel_repo in target_repo.rhel_repos:
            if rhel_repo.uid in rhsm_info.available_repos:
                repositories_to_use.append(rhel_repo.uid)
    return repositories_to_use


@with_rhsm
def unset_release(context):
    """
    Unsets the configured release from the subscription manager so we can perform the upgrade.
    Stores the previous set release in self.info if not already received.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'release', '--unset'], split=False)


@with_rhsm
def set_release(context, release):
    """
    This function will set the version specified.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param release: Release to set the subscription manager to.
    :type release: str
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'release', '--set', release], split=False)


@with_rhsm
def restore_release(context, rhsm_info):
    """
    If a release has been set, this function will restore it from the rhsm_info.release value.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if rhsm_info.release:
        set_release(context, rhsm_info.release)


@with_rhsm
def get_release(context, rhsm_info):
    """
    Retrieves the release the subscription manager has been pinned to, if applicable.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if rhsm_info.release is None:
        with _handle_rhsm_exceptions():
            result = context.call(['subscription-manager', 'release'], split=False)
            result = _RE_RELEASE.findall(result['stdout'])
            rhsm_info.release = result[0] if result else ''


@with_rhsm
def refresh(context):
    """
    Calls 'subscription-manager refresh'

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    """
    with _handle_rhsm_exceptions():
        context.call(['subscription-manager', 'refresh'], split=False)


@with_rhsm
def get_existing_product_certificates(context, rhsm_info):
    """
    Retrieves information about existing product certificates on the system.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    if not rhsm_info.existing_product_certificates:
        for path in ('/etc/pki/product', '/etc/pki/product-default'):
            if not os.path.isdir(context.full_path(path)):
                continue
            certs = [os.path.join(path, f) for f in os.listdir(context.full_path(path))
                     if os.path.isfile(os.path.join(context.full_path(path), f))]
            if not certs:
                continue
            rhsm_info.existing_product_certificates.extend(certs)


@contextlib.contextmanager
def switched_certificate(context, rhsm_info, cert_path, version):
    """
    Performs all actions needed to switch the product certificate passed.

    This function will copy the certificate to /etc/pki/product and if necessary /etc/pki/product-default and
    removes other product certificates from there. Unsets the release and refreshes the subscription-manager.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    :param cert_path: Path to the product certificate to switch to.
    :type cert_path: string
    """
    if skip_rhsm():
        yield TargetRHSMInfo()
        return

    # Make a backup of product certificates
    pki_path = '/etc/pki'
    pki_backup_path = '/etc/pki.bak'
    context.call(['rm', '-rf', pki_backup_path], checked=False)
    context.call(['cp', '-a', pki_path, pki_backup_path], checked=False)

    for existing in rhsm_info.existing_product_certificates:
        try:
            context.remove(existing)
        except OSError:
            api.current_logger().warn('Failed to remove existing certificate: %s', existing, exc_info=True)

    for path in ('/etc/pki/product', '/etc/pki/product-default'):
        if os.path.isdir(context.full_path(path)):
            context.copy_to(cert_path, os.path.join(path, os.path.basename(cert_path)))

    unset_release(context)
    try:
        refresh(context)
        set_release(context, version)
        target_rhsm_info = TargetRHSMInfo()
        scan_rhsm_info(context, target_rhsm_info)
        yield target_rhsm_info
    finally:
        # Restore backup of product certificates
        context.call(['rm', '-rf', pki_path], checked=False)
        context.call(['cp', '-a', pki_backup_path, pki_path], checked=False)
        unset_release(context)
        # Restore release
        restore_release(context, rhsm_info)


@with_rhsm
def scan_rhsm_info(context, rhsm_info):
    """
    Gathers all RHSM information

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param rhsm_info: An instance of a RHSMInfo derived model.
    :type rhsm_info: RHSMInfo derived model
    """
    get_attached_skus(context, rhsm_info)
    get_available_repo_uids(context, rhsm_info)
    get_enabled_repo_uids(context, rhsm_info)
    get_release(context, rhsm_info)
    get_existing_product_certificates(context, rhsm_info)
