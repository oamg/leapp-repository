from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class CustomCryptoPolicy(Model):
    """
    Provides information about custom crypto policy found on the source system.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """
    The policy name, derived from the filename.
    """

    path = fields.String()
    """
    The path to the policy file to be copied to the target system.
    """


class CustomCryptoPolicyModule(CustomCryptoPolicy):
    """
    Internally, this carries the same information as CustomCryptoPolicy model,
    but the path will point to different directory as the semantics of the files
    is different.
    """


class CryptoPolicyInfo(Model):
    """
    Provide information related to crypto policies
    """
    topic = SystemInfoTopic

    current_policy = fields.String()
    """
    The current used crypto policy: /etc/crypto-policies/state/current

    Contains e.g. 'LEGACY', 'DEFAULT', ...
    """

    custom_policies = fields.List(fields.Model(CustomCryptoPolicy))
    """
    This is the list of custom crypto policies with *.pol extension found under the following
    directories that are not part of any RPM package:

    * /usr/share/crypto-policies/policies/
    * /etc/crypto-policies/policies/

    """

    custom_modules = fields.List(fields.Model(CustomCryptoPolicyModule))
    """
    This is the list of custom crypto policies modules with *.pmod extension found under the
    following directories that are not part of any RPM package:

    * /usr/share/crypto-policies/policies/modules/
    * /etc/crypto-policies/policies/modules/

    """
