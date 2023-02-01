from leapp.libraries.stdlib import CalledProcessError, run


def selinux_set_permissive():
    """ Set SElinux to permissive mode if it was in enforcing mode """
    cmd = ['/bin/sed', '-i', 's/^SELINUX=enforcing/SELINUX=permissive/g', '/etc/selinux/config']
    try:
        run(cmd)
    except CalledProcessError as e:
        return False, e.output
    return True, None
