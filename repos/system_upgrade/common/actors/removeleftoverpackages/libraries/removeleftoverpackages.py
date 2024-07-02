from leapp.libraries.common.rhsm import skip_rhsm
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import LeftoverPackages, RemovedPackages, RPM


def _get_leftover_packages():
    """
    Consume and return LefoverPackages, if there are none, return None
    """
    leftover_packages = next(api.consume(LeftoverPackages), LeftoverPackages())
    if not leftover_packages.items:
        api.current_logger().info('No leftover packages, skipping...')
        return None
    return leftover_packages


def _get_removed_packages(installed_rpms):
    """
    Create RemovedPackages message with the list of removed packages
    """
    removed_packages = RemovedPackages()
    removed = list(set(installed_rpms) - set(get_installed_rpms()))

    for pkg in removed:
        name, version, release, epoch, packager, arch, pgpsig = pkg.split('|')
        removed_packages.items.append(RPM(
            name=name,
            version=version,
            epoch=epoch,
            packager=packager,
            arch=arch,
            release=release,
            pgpsig=pgpsig
        ))
    return removed_packages


def process():
    leftover_packages = _get_leftover_packages()
    if leftover_packages is None:
        return

    installed_rpms = get_installed_rpms()

    to_remove = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in leftover_packages.items]
    cmd = ['dnf', 'remove', '-y', '--noautoremove'] + to_remove
    if skip_rhsm():
        # ensure we don't use suscription-manager when it should be skipped
        cmd += ['--disableplugin', 'subscription-manager']
    try:
        run(cmd)
    except (CalledProcessError, OSError):
        error = 'Failed to remove packages: {}'.format(', '.join(to_remove))
        api.current_logger().error(error)
        return

    api.produce(_get_removed_packages(installed_rpms))
