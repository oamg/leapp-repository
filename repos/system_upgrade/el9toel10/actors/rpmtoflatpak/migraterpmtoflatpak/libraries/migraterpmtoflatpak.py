from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import RpmToFlatpakFacts


def _install_preinstall_packages(preinstall_pkgs):
    cmd = ['dnf', 'install', '-y'] + preinstall_pkgs
    try:
        run(cmd)
    except (CalledProcessError, OSError) as e:
        api.current_logger().error(
            'Failed to install flatpak preinstall packages {}: {}'.format(
                ', '.join(preinstall_pkgs), e
            )
        )
        return False
    return True


def _run_flatpak_preinstall():
    try:
        run(['flatpak', 'preinstall', '--system', '--noninteractive'])
    except (CalledProcessError, OSError) as e:
        api.current_logger().error('Failed to run flatpak preinstall: {}'.format(e))
        return False
    return True


def process():
    facts = next(api.consume(RpmToFlatpakFacts), None)
    if not facts or not facts.packages:
        return

    preinstall_pkgs = [p.preinstall_pkg for p in facts.packages]
    rpm_names = [p.rpm_name for p in facts.packages]

    api.current_logger().info(
        'Migrating packages from RPM to Flatpak: {}'.format(', '.join(sorted(rpm_names)))
    )

    if not _install_preinstall_packages(preinstall_pkgs):
        return

    _run_flatpak_preinstall()
