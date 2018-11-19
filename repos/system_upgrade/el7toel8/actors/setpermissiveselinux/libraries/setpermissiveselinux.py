import subprocess


def selinux_set_permissive():
    """ Set SElinux to permissive mode if it was in enforcing mode """
    cmd = ['/bin/sed', '-i', 's/^SELINUX=enforcing/SELINUX=permissive/g', '/etc/selinux/config']
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return False, e.output
    else:
        return True, None
