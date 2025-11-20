import os
import shutil

from leapp.libraries.common import multipathutil
from leapp.libraries.stdlib import api
from leapp.models import UpdatedMultipathConfig

MODIFICATIONS_STORE_PATH = '/var/lib/leapp/proposed_modifications'

_regexes = ('vendor', 'product', 'revision', 'product_blacklist', 'devnode',
            'wwid', 'property', 'protocol')


def _update_config(need_foreign, need_allow_usb, config):
    if not (need_foreign or need_allow_usb or config.invalid_regexes_exist):
        return None
    contents = multipathutil.read_config(config.pathname)
    if contents is None:
        return None
    lines = contents.split('\n')

    section = None
    in_subsection = False
    updated_file = False
    defaults_start = -1
    for i, line in enumerate(lines):
        try:
            data = multipathutil.LineData(line, section, in_subsection)
        except ValueError:
            continue
        if data.type == data.TYPE_SECTION_END:
            if in_subsection:
                in_subsection = False
            elif section is not None:
                section = None
        elif data.type == data.TYPE_SECTION_START:
            if section is None:
                section = data.section
                if section == 'defaults':
                    defaults_start = i + 1
            elif not in_subsection:
                in_subsection = True
        elif data.type == data.TYPE_OPTION:
            if section == 'defaults':
                if data.option == 'enable_foreign':
                    need_foreign = False
                elif data.option == 'allow_usb_devices':
                    need_allow_usb = False
            if data.option in _regexes and data.value == '*':
                lines[i] = line.replace('*', '.*', 1)
                lines[i] += ' # line modified by Leapp'
                updated_file = True

    if need_foreign or need_allow_usb:
        updated_file = True
        if defaults_start < 0:
            if in_subsection:
                lines.append('\t} # line added by Leapp')
            if section is not None:
                lines.append('} # line added by Leapp')
            lines.append('defaults { # section added by Leapp')
            if need_foreign:
                lines.append('\tenable_foreign ""')
            if need_allow_usb:
                lines.append('\tallow_usb_devices yes')
            lines.append('}')
            lines.append('')
        else:
            if need_allow_usb:
                lines.insert(defaults_start, '\tallow_usb_devices yes # line added by Leapp')
            if need_foreign:
                lines.insert(defaults_start, '\tenable_foreign "" # line added by Leapp')

    if not updated_file:
        return None

    contents = '\n'.join(lines)
    return contents


def prepare_destination_for_file(file_path):
    dirname = os.path.dirname(file_path)
    os.makedirs(dirname, exist_ok=True)


def prepare_place_for_config_modifications(workspace_path=MODIFICATIONS_STORE_PATH):
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)
    os.mkdir(workspace_path)


def update_configs(facts):
    need_foreign = not any(x for x in facts.configs if x.enable_foreign_exists)
    need_allow_usb = not any(x for x in facts.configs if x.allow_usb_exists)

    config_updates = []
    prepare_place_for_config_modifications()

    for config in facts.configs:
        original_config_location = config.pathname

        rootless_path = config.pathname.lstrip('/')
        path_to_config_copy = os.path.join(MODIFICATIONS_STORE_PATH, rootless_path)
        api.current_logger().debug(
            'Instead of modyfing {}, preparing modified config at {}'.format(
                config.pathname,
                path_to_config_copy
            )
        )
        updated_config_location = path_to_config_copy

        contents = _update_config(need_foreign, need_allow_usb, config)
        need_foreign = False
        need_allow_usb = False
        """
        foreign_exists and allow_usb_exists only matter for the main
        config file.
        """
        if contents:
            prepare_destination_for_file(updated_config_location)
            multipathutil.write_config(updated_config_location, contents)

            update = UpdatedMultipathConfig(updated_config_location=updated_config_location,
                                            target_path=original_config_location)
            config_updates.append(update)

    api.produce(*config_updates)
