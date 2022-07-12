import warnings

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import module as module_lib
from leapp.libraries.common import rpms
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RPM

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
        # NOTE: currently we do not initialize/load DNF plugins here as we are
        # working just with the local stuff (load_system_repo=True)
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
        There's no yum module for py3. The dnf module can be used only on RHEL 8+,
        on RHEL 7 there's a bug in dnf preventing us to do so:
        https://bugzilla.redhat.com/show_bug.cgi?id=1789840
    """
    if not no_yum:
        return _get_package_repository_data_yum()
    if not no_dnf:
        return _get_package_repository_data_dnf()
    raise StopActorExecutionError(message=no_yum_warning_msg)


def map_modular_rpms_to_modules():
    """
    Map modular packages to the module streams they come from.
    """
    modules = module_lib.get_modules()
    # empty on RHEL 7 because of no modules
    if not modules:
        return {}
    # create a reverse mapping from the RPMS to module streams
    # key: tuple of 4 strings representing a NVRA (name, version, release, arch) of an RPM
    # value: tuple of 2 strings representing a module and its stream
    rpm_streams = {}
    for module in modules:
        for rpm in module.getArtifacts():
            # we transform the NEVRA string into a tuple
            name, epoch_version, release_arch = rpm.rsplit('-', 2)
            epoch, version = epoch_version.split(':', 1)
            release, arch = release_arch.rsplit('.', 1)
            rpm_key = (name, epoch, version, release, arch)
            # stream could be int or float, convert it to str just in case
            rpm_streams[rpm_key] = (module.getName(), str(module.getStream()))
    return rpm_streams


# TODO(drehak) unit tests
def process():
    output = rpms.get_installed_rpms()
    pkg_repos = get_package_repository_data()
    rpm_streams = map_modular_rpms_to_modules()

    result = InstalledRPM()
    for entry in output:
        entry = entry.strip()
        if not entry:
            continue
        name, version, release, epoch, packager, arch, pgpsig = entry.split('|')
        repository = pkg_repos.get(name, '')
        rpm_key = (name, epoch, version, release, arch)
        module, stream = rpm_streams.get(rpm_key, (None, None))
        result.items.append(RPM(
            name=name,
            version=version,
            epoch=epoch,
            packager=packager,
            arch=arch,
            release=release,
            pgpsig=pgpsig,
            repository=repository,
            module=module,
            stream=stream))
    api.produce(result)
