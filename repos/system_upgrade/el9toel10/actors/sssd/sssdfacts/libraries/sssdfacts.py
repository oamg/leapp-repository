import os

from leapp.exceptions import StopActorExecutionError
from leapp.models import SSSDConfig


def _look_for_files(expression: str, files: list[str]) -> list[str]:
    found = []

    for file in files:
        if os.path.isdir(file):
            found += _look_for_files(expression, [file + '/' + x for x in os.listdir(file)])
        else:
            try:
                with open(file, 'r') as f:
                    if expression in f.read():
                        found.append(file)
            except FileNotFoundError:
                pass
            except OSError as e:
                raise StopActorExecutionError('Could not open file ' + file, details={'details': str(e)})

    return found


def get_facts(sssd_config: list[str], ssh_config: str) ->SSSDConfig:
    """
    Check SSSD and SSH configuration related to the sss_ssh_knownhostsproxy tool.

    Checks:
        - Which files in the SSSD configuration include the `service` keyword,
        - Which files in the SSH configuration mention the tool.
    """

    sssd_files = _look_for_files('services', sssd_config)
    ssh_files = _look_for_files('sss_ssh_knownhostsproxy', ssh_config)

    return SSSDConfig(sssd_config_files = sssd_files, ssh_config_files = ssh_files)
