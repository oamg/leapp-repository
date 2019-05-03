

def semantics_changes(config):
    globally_enabled = False
    in_match_disabled = False
    for opt in config.permit_root_login:
        if opt.value != "yes" and opt.in_match is not None \
                and opt.in_match[0].lower() != 'all':
            in_match_disabled = True

        if opt.value == "yes" and (opt.in_match is None or
                                   opt.in_match[0].lower() == 'all'):
            globally_enabled = True

    return not globally_enabled and in_match_disabled
