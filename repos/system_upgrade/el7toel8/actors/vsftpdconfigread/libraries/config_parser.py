class ParsingError(Exception):
    pass


class VsftpdConfigOptionParser(object):
    def _get_string_options(self):
        return ["secure_chroot_dir", "ftp_username", "chown_username", "xferlog_file",
                "vsftpd_log_file", "message_file", "nopriv_user", "ftpd_banner",
                "banned_email_file", "chroot_list_file", "pam_service_name", "guest_username",
                "userlist_file", "anon_root", "local_root", "banner_file", "pasv_address",
                "listen_address", "user_config_dir", "listen_address6", "cmds_allowed",
                "hide_file", "deny_file", "user_sub_token", "email_password_file",
                "rsa_cert_file", "dsa_cert_file", "dh_param_file", "ecdh_param_file",
                "ssl_ciphers", "rsa_private_key_file", "dsa_private_key_file", "ca_certs_file",
                "cmds_denied"]

    def _get_boolean_options(self):
        return ["anonymous_enable", "local_enable", "pasv_enable", "port_enable",
                "chroot_local_user", "write_enable", "anon_upload_enable",
                "anon_mkdir_write_enable", "anon_other_write_enable", "chown_uploads",
                "connect_from_port_20", "xferlog_enable", "dirmessage_enable",
                "anon_world_readable_only", "async_abor_enable", "ascii_upload_enable",
                "ascii_download_enable", "one_process_model", "xferlog_std_format",
                "pasv_promiscuous", "deny_email_enable", "chroot_list_enable",
                "setproctitle_enable", "text_userdb_names", "ls_recurse_enable",
                "log_ftp_protocol", "guest_enable", "userlist_enable", "userlist_deny",
                "use_localtime", "check_shell", "hide_ids", "listen", "port_promiscuous",
                "passwd_chroot_enable", "no_anon_password", "tcp_wrappers", "use_sendfile",
                "force_dot_files", "listen_ipv6", "dual_log_enable", "syslog_enable",
                "background", "virtual_use_local_privs", "session_support", "download_enable",
                "dirlist_enable", "chmod_enable", "secure_email_list_enable",
                "run_as_launching_user", "no_log_lock", "ssl_enable", "allow_anon_ssl",
                "force_local_logins_ssl", "force_local_data_ssl", "ssl_sslv2", "ssl_sslv3",
                "ssl_tlsv1", "ssl_tlsv1_1", "ssl_tlsv1_2", "tilde_user_enable",
                "force_anon_logins_ssl", "force_anon_data_ssl", "mdtm_write",
                "lock_upload_files", "pasv_addr_resolve", "reverse_lookup_enable",
                "userlist_log", "debug_ssl", "require_cert", "validate_cert",
                "strict_ssl_read_eof", "strict_ssl_write_shutdown", "ssl_request_cert",
                "delete_failed_uploads", "implicit_ssl", "ptrace_sandbox", "require_ssl_reuse",
                "isolate", "isolate_network", "ftp_enable", "http_enable", "seccomp_sandbox",
                "allow_writeable_chroot", "better_stou", "log_die"]

    def _get_integer_options(self):
        return ["accept_timeout", "connect_timeout", "local_umask", "anon_umask",
                "ftp_data_port", "idle_session_timeout", "data_connection_timeout",
                "pasv_min_port", "pasv_max_port", "anon_max_rate", "local_max_rate",
                "listen_port", "max_clients", "file_open_mode", "max_per_ip", "trans_chunk_size",
                "delay_failed_login", "delay_successful_login", "max_login_fails",
                "chown_upload_mode", "bind_retries"]

    def _get_boolean(self, option, value):
        value = value.upper()
        if value in ['YES', 'TRUE', '1']:
            return True
        if value in ['NO', 'FALSE', '0']:
            return False
        raise ParsingError("Boolean option '%s' contains a non-boolean value '%s'"
                           % (option, value))

    def _get_integer(self, option, value):
        try:
            return int(value)
        except ValueError:
            raise ParsingError("Integer option '%s' contains a non-integer value '%s'"
                               % (option, value))

    def parse_value(self, option, value):
        if option in self._get_string_options():
            return value
        if option in self._get_boolean_options():
            return self._get_boolean(option, value)
        if option in self._get_integer_options():
            return self._get_integer(option, value)

        raise ParsingError("Unknown option: '%s'" % option)


class VsftpdConfigParser(object):
    def __init__(self, config_content):
        self._option_parser = VsftpdConfigOptionParser()
        self.parsed_config = self._parse_config(config_content)

    def _parse_config_line(self, line, conf_dict):
        if not line or line.startswith('#') or line.isspace():
            return
        try:
            option, value = line.split('=', 1)
        except ValueError:
            raise ParsingError("The line does not have the form 'option=value': %s" % line)
        option = option.strip()
        value = value.strip()
        value = self._option_parser.parse_value(option, value)
        conf_dict[option] = value

    def _parse_config(self, contents):
        res = {}
        for (ix, line) in enumerate(contents.split('\n')):
            try:
                self._parse_config_line(line, res)
            except ParsingError as e:
                raise ParsingError("Syntax error on line %d: %s" % (ix + 1, e))
        return res
