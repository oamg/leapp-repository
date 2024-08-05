import os
import re

from leapp.models import PamUserDbLocation


def _parse_pam_config_file(conf_file):
    with open(conf_file, 'r') as file:
        for line in file:
            if 'pam_userdb' in line:
                match = re.search(r'db=(\S+)', line)
                if match:
                    return match.group(1)

    return None


def parse_pam_config_folder(conf_folder):
    locations = set()

    for file_name in os.listdir(conf_folder):
        file_path = os.path.join(conf_folder, file_name)

        if os.path.isfile(file_path):
            location = _parse_pam_config_file(file_path)
            if location is not None:
                locations.add(location)

    return PamUserDbLocation(locations=list(locations))
