from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import RpmToFlatpakFacts


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

    rpm_names = sorted(p.rpm_name for p in facts.packages)
    api.current_logger().info(
        'Migrating packages from RPM to Flatpak: {}'.format(', '.join(rpm_names))
    )

    _run_flatpak_preinstall()
