import re

from leapp.libraries.common import multipathutil

_bool_options = {'retain_attached_hw_handler': True, 'detect_prio': True,
                 'detect_path_checker': True, 'reassign_maps': False}

_exist_options = ('hw_str_match', 'ignore_new_boot_devs',
                  'new_bindings_in_boot', 'unpriv_sgio')

_ovr_options = ('hardware_handler', 'pg_timeout')


class _QueueIfNoPathInfo(object):
    def __init__(self, line, value):
        self.line = line
        self.value = value
        self.has_no_path_retry = False


def _nothing_to_do(config):
    if config.default_path_checker and config.default_path_checker != 'tur':
        return False

    config_checks = (
        (config.default_retain_hwhandler, False),
        (config.default_detect_prio, False),
        (config.default_detect_checker, False),
        (config.reassign_maps, True),
        (config.hw_str_match_exists, True),
        (config.ignore_new_boot_devs_exists, True),
        (config.new_bindings_in_boot_exists, True),
        (config.unpriv_sgio_exists, True),
        (config.detect_path_checker_exists, True),
        (config.overrides_hwhandler_exists, True),
        (config.overrides_pg_timeout_exists, True),
        (config.queue_if_no_path_exists, True),
        (config.all_devs_section_exists, True)
    )
    for option, value in config_checks:
        if option is value:
            return False

    return config.all_devs_options == []


def _comment_out_line(line):
    return '# ' + line + ' # Commented out by Leapp'


def _comment_out_ranges(lines, ranges):
    for start, end in ranges:
        line = lines[start]
        lines[start] = '# ' + line + ' # Section commented out by Leapp'
        for i in range(start + 1, end):
            line = lines[i]
            if line == '':
                lines[i] = '#'
            elif line[0] != '#':
                lines[i] = '# ' + line


def _setup_value(value):
    if re.search(r'\s', value):
        return '"' + value + '"'
    return value


def _add_overrides(lines, options):
    lines.append('overrides { # Section added by Leapp')
    for option in options:
        lines.append('\t{} {}'.format(option.name, _setup_value(option.value)))
    lines.append('}')
    lines.append('')


def _update_overrides(lines, ovr_line, options):
    new_lines = []
    start = None
    for i, line in enumerate(lines):
        if line is ovr_line:
            start = i + 1
            break
    if not start:
        return
    for option in options:
        new_lines.append('\t{} {} # Line added by Leapp'.
                         format(option.name, _setup_value(option.value)))
    lines[start:start] = new_lines      # insert new_lines


def _convert_checker_line(line):
    return line.replace('detect_path_checker', 'detect_checker') + \
            ' # Line modified by Leapp'


def _modify_features_line(line, value):
    items = value.split()
    if items == [] or not items[0].isdigit():
        return _comment_out_line(line)
    nr_features = int(items[0])
    if nr_features != len(items) - 1:
        return _comment_out_line(line)
    r = re.match('^(.*)features', line)
    if not r:
        return _comment_out_line(line)
    line_start = r.group(1)
    try:
        items.remove('queue_if_no_path')
    except ValueError:
        return _comment_out_line(line)
    items[0] = str(nr_features - 1)
    return line_start + 'features "' + ' '.join(items) + \
        '" # Line modified by Leapp'


def _add_npr(lines, line, i):
    r = re.match('^(.*)features', line)
    if not r:
        return
    line_start = r.group(1)
    lines.insert(i,
                 line_start + 'no_path_retry queue # Line added by Leapp')


def _remove_qinp(lines, qinp_infos):
    infos_iter = iter(qinp_infos)
    info = next(infos_iter, None)
    if not info:
        return
    i = 0
    while i < len(lines):
        if lines[i] is info.line:
            lines[i] = _modify_features_line(info.line, info.value)
            if not info.has_no_path_retry:
                _add_npr(lines, info.line, i + 1)
            info = next(infos_iter, None)
            if not info:
                return
        i += 1


def _valid_npr(value):
    if value.isdigit() and int(value) >= 0:
        return True
    if value in ('fail', 'queue'):
        return True
    return False


def _update_config(config):
    if _nothing_to_do(config):
        return None
    contents = multipathutil.read_config(config.pathname)
    if contents is None:
        return None
    lines = contents.split('\n')
    section = None
    in_subsection = False
    in_all_devs = False
    subsection_start = None
    all_devs_ranges = []
    overrides_line = None
    qinp_info = None
    has_no_path_retry = False
    qinp_infos = []
    for i, line in enumerate(lines):
        try:
            data = multipathutil.LineData(line, section, in_subsection)
        except ValueError:
            continue
        if data.type == data.TYPE_SECTION_END:
            if qinp_info and not in_all_devs:
                qinp_info.has_no_path_retry = has_no_path_retry
                qinp_infos.append(qinp_info)
            qinp_info = None
            has_no_path_retry = False
            if in_subsection:
                in_subsection = False
                if in_all_devs:
                    all_devs_ranges.append((subsection_start, i + 1))
                in_all_devs = False
                subsection_start = None
            elif section is not None:
                section = None
        elif data.type == data.TYPE_SECTION_START:
            if section is None:
                section = data.section
                if section == 'overrides':
                    overrides_line = line
            elif not in_subsection:
                in_subsection = True
                subsection_start = i
        if data.type != data.TYPE_OPTION:
            continue
        if section == 'defaults':
            if (data.option == 'path_checker' or data.option == 'checker') and \
                    data.value != 'tur':
                lines[i] = _comment_out_line(line)
                continue
            if data.option in _bool_options and \
                    _bool_options[data.option] != data.is_enabled():
                lines[i] = _comment_out_line(line)
                continue
        elif section == 'overrides' and data.option in _ovr_options:
            lines[i] = _comment_out_line(line)
            continue
        elif section == 'devices' and in_subsection and \
                data.option == 'all_devs' and data.is_enabled():
            in_all_devs = True
            continue
        if data.option in _exist_options:
            lines[i] = _comment_out_line(line)
        elif data.option == 'detect_path_checker':
            lines[i] = _convert_checker_line(line)
        elif data.option == 'no_path_retry' and _valid_npr(data.value):
            has_no_path_retry = True
        elif data.option == 'features' and 'queue_if_no_path' in data.value:
            qinp_info = _QueueIfNoPathInfo(line, data.value)

    if in_subsection:
        lines.append('\t} # line added by Leapp')
        if in_all_devs:
            all_devs_ranges.append((subsection_start, len(lines)))
        elif qinp_info:
            qinp_info.has_no_path_retry = has_no_path_retry
            qinp_infos.append(qinp_info)
            qinp_info = None
    if section is not None:
        lines.append('} # line added by Leapp')
        lines.append('')
        if qinp_info:
            qinp_info.has_no_path_retry = has_no_path_retry
            qinp_infos.append(qinp_info)
    _comment_out_ranges(lines, all_devs_ranges)
    if qinp_infos != []:
        _remove_qinp(lines, qinp_infos)
    if config.all_devs_options != []:
        if overrides_line:
            _update_overrides(lines, overrides_line, config.all_devs_options)
        else:
            _add_overrides(lines, config.all_devs_options)
    contents = '\n'.join(lines)
    return contents


def update_configs(facts):
    for config in facts.configs:
        contents = _update_config(config)
        if contents:
            multipathutil.write_config(config.pathname, contents)
