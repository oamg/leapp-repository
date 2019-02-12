import dbus


def is_hexstring(s):
    arr = s.split(':')
    for a in arr:
        if len(a) != 1 and len(a) != 2:
            return False
        try:
            h = int(a, 16)
        except ValueError as e:
            return False
    return True

def update_client_ids(logger):
    ''' Updates client-ids of NetworkManager connections through D-Bus '''
    try:
        bus = dbus.SystemBus()
        proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
        settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
        connections = settings.ListConnections()
    except dbus.exceptions.DBusException as e:
        logger.warn('Can\'t connect to NetworkManager: {}'.format(e))
        return

    processed = 0
    changed = 0
    errors = 0

    for c_path in connections:
        processed += 1
        try:
            c_proxy = bus.get_object("org.freedesktop.NetworkManager", c_path)
            c_obj = dbus.Interface(c_proxy, "org.freedesktop.NetworkManager.Settings.Connection")
            c_settings = c_obj.GetSettings()
        except dbus.exceptions.DBusException as e:
            logger.warn('Failed to get connection settings: {}'.format(e))
            errors += 1
            continue

        if 'ipv4' not in c_settings:
            continue
        if 'dhcp-client-id' not in c_settings['ipv4']:
            continue

        client_id = c_settings['ipv4']['dhcp-client-id']
        if is_hexstring(client_id):
            continue

        new_client_id = ':'.join(hex(ord(x))[2:] for x in client_id)
        c_settings['ipv4']['dhcp-client-id'] = new_client_id

        try:
            c_obj.Update(c_settings)
            changed += 1
            success = True
        except dbus.exceptions.DBusException as e:
            logger.warn('Failed to update connection: {}'.format(e))
            errors += 1
            success = False
            
        logger.info('Connection {}: \'{}\' -> \'{}\' ({})'.format(c_settings['connection']['uuid'],
                                                                  client_id, new_client_id,
                                                                  'OK' if success else 'FAIL'))

    logger.info("{} processed, {} changed, {} errors".format(processed, changed, errors))
