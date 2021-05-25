import warnings

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.module import get_modules, map_installed_rpms_to_modules

no_yum = False
no_yum_warning_msg = "package `yum` is unavailable"
try:
    import yum
except ImportError:
    no_yum = True
    warnings.warn(no_yum_warning_msg, ImportWarning)

no_dnf = False
no_dnf_warning_msg = "package `dnf` is unavailable"
try:
    import dnf
except ImportError:
    no_dnf = True
    warnings.warn(no_dnf_warning_msg, ImportWarning)


def _get_package_repository_data_yum():
    yum_base = yum.YumBase()
    pkg_repos = {}

    try:
        for pkg in yum_base.doPackageLists().installed:
            pkg_repos[pkg.name] = pkg.ui_from_repo.lstrip('@')
    except ValueError as e:
        if 'locale' not in str(e):  # reraise if error is not related to locales
            raise e
        raise StopActorExecutionError(
            message='Failed to get installed RPM packages because of an invalid locale',
            details={
                'hint': 'Please run leapp with a valid locale. ' +
                        'You can get a list of installed locales by running `locale -a`.'
            })

    return pkg_repos


def _get_package_repository_data_dnf():
    dnf_base = dnf.Base()
    pkg_repos = {}

    try:
        dnf_base.fill_sack(load_system_repo=True, load_available_repos=False)
        for pkg in dnf_base.sack.query():
            pkg_repos[pkg.name] = pkg._from_repo.lstrip('@')
    except ValueError as e:
        if 'locale' not in str(e):  # reraise if error is not related to locales
            raise e
        raise StopActorExecutionError(
            message='Failed to get installed RPM packages because of an invalid locale',
            details={
                'hint': 'Please run leapp with a valid locale. ' +
                        'You can get a list of installed locales by running `locale -a`.'
            })

    return pkg_repos


def get_package_repository_data():
    """ Return dictionary mapping package name with repository from which it was installed.
    Note:
        There's no yum module for py3. The dnf module can be used only on RHEL 8,
        on RHEL 7 there's a bug in dnf preventing us to do so:
        https://bugzilla.redhat.com/show_bug.cgi?id=1789840
    """
    if not no_yum:
        return _get_package_repository_data_yum()
    if not no_dnf:
        return _get_package_repository_data_dnf()
    raise StopActorExecutionError(message=no_yum_warning_msg)
