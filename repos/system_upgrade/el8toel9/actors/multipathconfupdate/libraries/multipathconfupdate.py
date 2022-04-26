from leapp.libraries.common import multipathutil

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


def update_configs(facts):
    need_foreign = not any(x for x in facts.configs if x.enable_foreign_exists)
    need_allow_usb = not any(x for x in facts.configs if x.allow_usb_exists)
    for config in facts.configs:
        contents = _update_config(need_foreign, need_allow_usb, config)
        need_foreign = False
        need_allow_usb = False
        """
        foreign_exists and allow_usb_exists only matter for the main
        config file.
        """
        if contents:
            multipathutil.write_config(config.pathname, contents)
