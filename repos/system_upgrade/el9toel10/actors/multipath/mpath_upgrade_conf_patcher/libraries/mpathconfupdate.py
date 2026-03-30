import os
import shutil

from leapp.libraries.common import multipathutil
from leapp.libraries.stdlib import api
from leapp.models import MultipathConfigUpdatesInfo, UpdatedMultipathConfig

MODIFICATIONS_STORE_PATH = '/var/lib/leapp/proposed_modifications'

_DEFAULT_CONFIG_DIR = '/etc/multipath/conf.d'
_DEFAULT_BINDINGS_FILE = '/etc/multipath/bindings'
_DEFAULT_WWIDS_FILE = '/etc/multipath/wwids'
_DEFAULT_PRKEYS_FILE = '/etc/multipath/prkeys'

_deprecated_options = ('config_dir', 'bindings_file', 'wwids_file', 'prkeys_file')


def _update_config(config):
    contents = multipathutil.read_config(config.pathname)
    if contents is None:
        return None
    lines = contents.split('\n')

    section = None
    in_subsection = False
    updated_file = False
    comment_lines = []
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
            elif not in_subsection:
                in_subsection = True
        elif data.type == data.TYPE_OPTION:
            if section == 'defaults' and data.option in _deprecated_options:
                comment_lines.append(i)
                updated_file = True

    if not updated_file:
        return None

    for i in reversed(comment_lines):
        lines[i] = '#{}  # line commented out by leapp'.format(lines[i])

    return '\n'.join(lines)


def _get_file_locations(facts):
    bindings_file = None
    wwids_file = None
    prkeys_file = None
    for conf in facts.configs:
        if conf.bindings_file is not None:
            bindings_file = os.path.normpath(conf.bindings_file)
        if conf.wwids_file is not None:
            wwids_file = os.path.normpath(conf.wwids_file)
        if conf.prkeys_file is not None:
            prkeys_file = os.path.normpath(conf.prkeys_file)

    file_updates = []
    if bindings_file is not None and bindings_file != _DEFAULT_BINDINGS_FILE:
        file_updates.append((bindings_file, _DEFAULT_BINDINGS_FILE))
    if wwids_file is not None and wwids_file != _DEFAULT_WWIDS_FILE:
        file_updates.append((wwids_file, _DEFAULT_WWIDS_FILE))
    if prkeys_file is not None and prkeys_file != _DEFAULT_PRKEYS_FILE:
        file_updates.append((prkeys_file, _DEFAULT_PRKEYS_FILE))
    return file_updates


def prepare_destination_for_file(file_path):
    dirname = os.path.dirname(file_path)
    os.makedirs(dirname, exist_ok=True)


def prepare_place_for_config_modifications(workspace_path=MODIFICATIONS_STORE_PATH):
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)
    os.mkdir(workspace_path)


def update_configs(facts):
    if not facts.configs:
        return

    config_updates = []
    prepare_place_for_config_modifications()

    primary = facts.configs[0]
    non_default_config_dir = (
        primary.config_dir is not None
        and os.path.normpath(primary.config_dir) != _DEFAULT_CONFIG_DIR
    )

    for idx, config in enumerate(facts.configs):
        is_secondary = idx > 0

        if is_secondary:
            target_path = os.path.join(
                _DEFAULT_CONFIG_DIR, os.path.basename(config.pathname)
            )
        else:
            target_path = config.pathname

        contents = _update_config(config)

        if contents is not None:
            rootless_path = config.pathname.lstrip('/')
            updated_config_location = os.path.join(
                MODIFICATIONS_STORE_PATH, rootless_path
            )
            api.current_logger().debug(
                'Instead of modifying {}, preparing modified config at {}'.format(
                    config.pathname, updated_config_location
                )
            )
            prepare_destination_for_file(updated_config_location)
            multipathutil.write_config(updated_config_location, contents)
            config_updates.append(UpdatedMultipathConfig(
                updated_config_location=updated_config_location,
                target_path=target_path
            ))
        elif is_secondary and non_default_config_dir:
            config_updates.append(UpdatedMultipathConfig(
                updated_config_location=config.pathname,
                target_path=target_path
            ))

    for source_path, default_path in _get_file_locations(facts):
        config_updates.append(UpdatedMultipathConfig(
            updated_config_location=source_path,
            target_path=default_path
        ))

    api.produce(MultipathConfigUpdatesInfo(updates=config_updates))
