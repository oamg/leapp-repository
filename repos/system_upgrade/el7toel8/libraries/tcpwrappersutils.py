import re


def _build_regex(pattern):
    regex = '^'
    part_beginning = 0
    while part_beginning < len(pattern):
        ix1 = pattern.find('*', part_beginning)
        ix2 = pattern.find('?', part_beginning)
        ix1 = len(pattern) if ix1 < 0 else ix1
        ix2 = len(pattern) if ix2 < 0 else ix2
        part_end = min(ix1, ix2)

        regex += re.escape(pattern[part_beginning:part_end])

        if part_end < len(pattern):
            if pattern[part_end] == '*':
                regex += '.*'
            else:
                regex += '.'

        part_beginning = part_end + 1

    regex += '$'
    return regex


def _pattern_matches(pattern, string):
    if pattern.lower() == 'all':
        return True
    regex = _build_regex(pattern)
    return re.match(regex, string, re.IGNORECASE) is not None


def _daemon_list_matches_daemon(daemon_list, daemon, recursion_depth):
    try:
        cur_list_end = daemon_list.index('except')
    except ValueError:
        cur_list_end = len(daemon_list)
    cur_list = daemon_list[:cur_list_end]
    matches_cur_list = False
    for item in cur_list:
        try:
            ix = item.index('@')
            # For simplicity, we ignore the host part. So we must make sure
            # that a daemon list containing a host-based pattern will always match
            # the daemon part of that host-based pattern (e.g. 'all except vsftpd@localhost
            # matches 'vsftpd'). See test_config_applies_to_daemon_with_host_except().
            if recursion_depth % 2 == 1:
                continue
            pattern = item[:ix]
        except ValueError:
            pattern = item
        if _pattern_matches(pattern, daemon):
            matches_cur_list = True
            break

    next_list = daemon_list[cur_list_end + 1:]
    if not next_list:
        matches_next_list = False
    else:
        matches_next_list = _daemon_list_matches_daemon(next_list, daemon, recursion_depth + 1)

    return matches_cur_list and not matches_next_list


def config_applies_to_daemon(facts, daemon):
    '''
    Returns True if the specified tcp_wrappers configuration applies to the specified daemon.
    Otherwise returns False.

    This information is intended to be used in the Checks phase to check whether there is
    any tcp_wrappers configuration that the user needs to migrate manually and whether we
    should inhibit the upgrade, so that the upgraded system is not insecure.

    :param facts: A TcpWrappersFacts representation of the tcp_wrappers configuration
    :param daemon: The daemon name
    '''
    for daemon_list in facts.daemon_lists:
        value = [item.lower() for item in daemon_list.value]
        if _daemon_list_matches_daemon(value, daemon, 0):
            return True
    return False
