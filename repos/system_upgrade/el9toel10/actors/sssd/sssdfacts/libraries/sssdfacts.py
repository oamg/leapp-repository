import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import KnownHostsProxyConfig


def _does_file_contain_expression(file_path, expression):
    try:
        with open(file_path) as in_file:
            for line in in_file:
                if re.search(expression, line) is not None:
                    return True
        return False
    except FileNotFoundError:
        api.current_logger().warning(
            'Found a file during a recursive walk, but we failed to open it for reading: {}'.format(file_path)
        )
        return False
    except OSError as e:
        raise StopActorExecutionError('Could not open file ' + file_path, details={'details': str(e)})


def _look_for_files(expression: str, path_list: list[str]) -> list[str]:
    files_containing_expression = []
    for path in path_list:
        if os.path.isdir(path):
            for root, dummy_dirs, files in os.walk(path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if _does_file_contain_expression(full_path, expression):
                        files_containing_expression.append(full_path)
        else:
            if _does_file_contain_expression(path, expression):
                files_containing_expression.append(path)

    return files_containing_expression


def get_facts(sssd_config: list[str], ssh_config: list[str]) -> KnownHostsProxyConfig:
    """
    Check SSSD and SSH configuration related to the sss_ssh_knownhostsproxy tool.

    Checks:
        - Which files in the SSSD configuration include the `service` keyword,
        - Which files in the SSH configuration mention the tool.
    """

    sssd_files = _look_for_files(r'^\s*services\s*=', sssd_config)
    ssh_files = _look_for_files(r'^\s*#?\s*ProxyCommand\s+(/usr/bin/)?sss_ssh_knownhostsproxy\s', ssh_config)

    return KnownHostsProxyConfig(sssd_config_files=sssd_files, ssh_config_files=ssh_files)
