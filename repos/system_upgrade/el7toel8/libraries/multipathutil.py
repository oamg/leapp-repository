import errno
import re

from leapp.libraries.stdlib import api

_sections = ('defaults', 'blacklist', 'blacklist_exceptions', 'devices',
             'overrides', 'multipaths')

_subsections = {'blacklist': 'device', 'blacklist_exceptions': 'device',
                'devices': 'device', 'multipaths': 'multipath'}


def read_config(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            api.current_logger().debug(
                'multipath configuration file {} does not exist.'.format(path)
            )
        else:
            api.current_logger().warning(
                'Failed to read multipath configuration file {}: {}'.
                format(path, e)
            )
        return None


def write_config(path, contents):
    try:
        with open(path, 'w') as f:
            f.write(contents)
    except IOError as e:
        api.current_logger().warning(
            'Failed to write multipath configuration file {}: {}'.
            format(path, e)
        )


class LineData(object):
    TYPE_BLANK = 0
    TYPE_SECTION_START = 1
    TYPE_SECTION_END = 2
    TYPE_OPTION = 3

    def __init__(self, line, section, in_subsection):
        comment_pattern = re.compile('^([^"#!]*)[#!]')
        string_pattern = re.compile('^([^"]*)"([^"]*)')
        utf8_pattern = re.compile('[^\x00-\x7F]+')
        line_pattern = re.compile(r'^([^\s{}]+)\s*(\S*)')
        value = None

        r = comment_pattern.match(line)
        if r:
            line = r.group(1)
        r = string_pattern.match(line)
        if r:
            line = r.group(1)
            value = r.group(2)
        line = utf8_pattern.sub(' ', line)
        line = line.strip()

        if line == '':
            self.type = self.TYPE_BLANK
            return
        if line[0] == '}':
            self.type = self.TYPE_SECTION_END
            return

        r = line_pattern.match(line)
        if r is None:
            raise ValueError
        keyword = r.group(1)
        if r.group(2) != '':
            value = r.group(2)  # even if value was set before

        if section is None:
            if keyword in _sections:
                self.type = self.TYPE_SECTION_START
                self.section = keyword
                return
            raise ValueError

        if not in_subsection and section in _subsections and \
                keyword == _subsections[section]:
            self.type = self.TYPE_SECTION_START
            self.section = keyword
            return

        if value is None:
            raise ValueError
        self.type = self.TYPE_OPTION
        self.option = keyword
        self.value = value

    def is_enabled(self):
        if self.value == 'yes' or self.value == '1':
            return True
        if self.value == 'no' or self.value == '0':
            return False
        return None
