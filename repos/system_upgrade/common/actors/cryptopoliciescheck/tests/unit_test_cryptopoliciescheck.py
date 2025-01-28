from leapp.libraries.actor.cryptopoliciescheck import _get_files_to_copy
from leapp.models import CryptoPolicyInfo, CustomCryptoPolicy, CustomCryptoPolicyModule


def test_get_files_to_copy():
    cpi = CryptoPolicyInfo(current_policy="DEFAULT", custom_policies=[], custom_modules=[])
    assert _get_files_to_copy(cpi) == []

    cpi.custom_policies.append(CustomCryptoPolicy(name="CUSTOM", path="/path/to/CUSTOM.pol"))
    assert _get_files_to_copy(cpi) == ["/path/to/CUSTOM.pol"]

    cpi.custom_modules.append(CustomCryptoPolicyModule(name="FIX", path="/path/to/FIX.mpol"))
    assert _get_files_to_copy(cpi) == ["/path/to/CUSTOM.pol", "/path/to/FIX.mpol"]
