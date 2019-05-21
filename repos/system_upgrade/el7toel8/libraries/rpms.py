from leapp.libraries import stdlib
from leapp.models import InstalledRPM


def get_installed_rpms():
    rpm_cmd = [
        '/bin/rpm',
        '-qa',
        '--queryformat',
        r'%{NAME}|%{VERSION}|%{RELEASE}|%|EPOCH?{%{EPOCH}}:{(none)}||%|PACKAGER?{%{PACKAGER}}:{(none)}||%|'
        r'ARCH?{%{ARCH}}:{}||%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{(none)}|}|\n'
    ]
    try:
        return stdlib.run(rpm_cmd, split=True)['stdout']
    except stdlib.CalledProcessError as err:
        error = 'Execution of {CMD} returned {RC}. Unable to find installed packages.'.format(CMD=err.command,
                                                                                              RC=err.exit_code)
        stdlib.api.current_logger().error(error)
        return []


def create_lookup(model, field, key, context=stdlib.api):
    """
    Create a lookup set from one of the model fields.

    :param model: model class
    :param field: model field, its value will be taken for lookup data
    :param key: property of the field's data that will be used to build a resulting set
    :param context: context of the execution
    """
    data = getattr(next((m for m in context.consume(model)), model()), field)
    try:
        return {getattr(obj, key) for obj in data} if data else {}
    except TypeError:
        # data is not iterable, not lookup can be built
        stdlib.api.current_logger().error(
                "{model}.{field}.{key} is not iterable, can't build lookup".format(
                    model=model, field=field, key=key))
        return {}


def has_package(model, package_name, context=stdlib.api):
    """
    Expects a model InstalledRedHatSignedRPM or InstalledUnsignedRPM.
    Can be useful in cases like a quick item presence check, ex. check in actor that
    a certain package is installed.

    :param model: model class
    :param package_name: package to be checked
    """
    if not (isinstance(model, type) and issubclass(model, InstalledRPM)):
        return False
    return package_name in create_lookup(model, field='items', key='name', context=context)
