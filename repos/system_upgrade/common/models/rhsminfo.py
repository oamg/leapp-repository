from leapp.models import fields, Model
from leapp.topics import RHSMTopic


class RHSMInfo(Model):
    """
    Subscription-manager details required for the inplace upgrade.
    """
    topic = RHSMTopic

    release = fields.Nullable(fields.String())
    """ Release the subscription-manager is set to. """
    attached_skus = fields.List(fields.String(), default=[])
    """ SKUs the current system is attached to. """
    available_repos = fields.List(fields.String(), default=[])
    """ Repositories that are available to the current system through the subscription-manager. """
    enabled_repos = fields.List(fields.String(), default=[])
    """ Repositories that are enabled on the current system through the subscription-manager. """
    existing_product_certificates = fields.List(fields.String(), default=[])
    """ Product certificates that are currently installed on the system. """
    sca_detected = fields.Boolean(default=False)
    """ Info about whether SCA manifest was used or not. """
    is_registered = fields.Boolean(default=False)
    """
    Whether the system is registered through subscription-manager

    Note that this doesn't differentiate between a registration to an SKU or
    SCA organization.
    """
