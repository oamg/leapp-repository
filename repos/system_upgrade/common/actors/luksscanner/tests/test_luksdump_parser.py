import os

from leapp.libraries.actor.luksdump_parser import LuksDumpParser
from leapp.snactor.fixture import current_actor_context

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_luksdump_parser_luks1(current_actor_context):
    f = open(os.path.join(CUR_DIR, 'files/luksDump_nvme0n1p3_luks1.txt'))
    parsed_dict = LuksDumpParser.parse(f.readlines())

    assert parsed_dict["Version"] == "1"
    assert parsed_dict["Cipher name"] == "aes"
    assert parsed_dict["Cipher mode"] == "xts-plain64"
    assert parsed_dict["Hash spec"] == "sha256"
    assert parsed_dict["Payload offset"] == "4096"
    assert parsed_dict["MK bits"] == "512"
    assert parsed_dict["MK digest"].replace(" ", "") == "fbec6b31aee449033ead432202cfa878ad3cd2a8"
    assert parsed_dict["MK salt"].replace(" ", "") == "17574e2fed0b5c62d5de54f57fab6068"\
                                                      "71d87206646c810539553f553256d9da"
    assert parsed_dict["MK iterations"] == "114573"
    assert parsed_dict["UUID"] == "90242257-d00a-4019-aba6-03083f89404b"

    assert parsed_dict["Key Slot 0"]["enabled"]
    assert parsed_dict["Key Slot 0"]["Iterations"] == "1879168"
    assert parsed_dict["Key Slot 0"]["Salt"].replace(" ", "") == "fc774872bd31ca8323805a5eb95bdebb" \
                                                                 "55acd5a93b96ada582bc1168baf88756"
    assert parsed_dict["Key Slot 0"]["Key material offset"] == "8"
    assert parsed_dict["Key Slot 0"]["AF stripes"] == "4000"

    assert not parsed_dict["Key Slot 1"]["enabled"]
    assert not parsed_dict["Key Slot 2"]["enabled"]
    assert not parsed_dict["Key Slot 3"]["enabled"]
    assert not parsed_dict["Key Slot 4"]["enabled"]
    assert not parsed_dict["Key Slot 5"]["enabled"]
    assert not parsed_dict["Key Slot 6"]["enabled"]
    assert not parsed_dict["Key Slot 7"]["enabled"]


def test_luksdump_parser_luks2_tokens(current_actor_context):
    f = open(os.path.join(CUR_DIR, 'files/luksDump_nvme0n1p3_luks2_tokens.txt'))
    parsed_dict = LuksDumpParser.parse(f.readlines())

    assert parsed_dict["Version"] == "2"
    assert parsed_dict["Epoch"] == "9"
    assert parsed_dict["Metadata area"] == "16384 [bytes]"
    assert parsed_dict["Keyslots area"] == "16744448 [bytes]"
    assert parsed_dict["UUID"] == "6b929b85-b01e-4aa3-8ad2-a05decae6e3d"
    assert parsed_dict["Label"] == "(no label)"
    assert parsed_dict["Subsystem"] == "(no subsystem)"
    assert parsed_dict["Flags"] == "(no flags)"

    assert len(parsed_dict["Data segments"]) == 1
    assert parsed_dict["Data segments"]["0"]["type"] == "crypt"
    assert parsed_dict["Data segments"]["0"]["offset"] == "16777216 [bytes]"
    assert parsed_dict["Data segments"]["0"]["length"] == "(whole device)"
    assert parsed_dict["Data segments"]["0"]["cipher"] == "aes-xts-plain64"
    assert parsed_dict["Data segments"]["0"]["sector"] == "512 [bytes]"

    assert len(parsed_dict["Keyslots"]) == 4
    assert parsed_dict["Keyslots"]["0"]["type"] == "luks2"
    assert parsed_dict["Keyslots"]["0"]["Key"] == "512 bits"
    assert parsed_dict["Keyslots"]["0"]["Priority"] == "normal"
    assert parsed_dict["Keyslots"]["0"]["Cipher"] == "aes-xts-plain64"
    assert parsed_dict["Keyslots"]["0"]["Cipher key"] == "512 bits"
    assert parsed_dict["Keyslots"]["0"]["PBKDF"] == "argon2id"
    assert parsed_dict["Keyslots"]["0"]["Time cost"] == "7"
    assert parsed_dict["Keyslots"]["0"]["Memory"] == "1048576"
    assert parsed_dict["Keyslots"]["0"]["Threads"] == "4"
    assert parsed_dict["Keyslots"]["0"]["Salt"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Keyslots"]["0"]["AF stripes"] == "4000"
    assert parsed_dict["Keyslots"]["0"]["AF hash"] == "sha256"
    assert parsed_dict["Keyslots"]["0"]["Area offset"] == "32768 [bytes]"
    assert parsed_dict["Keyslots"]["0"]["Area length"] == "258048 [bytes]"
    assert parsed_dict["Keyslots"]["0"]["Digest ID"] == "0"

    assert parsed_dict["Keyslots"]["1"]["type"] == "luks2"
    assert parsed_dict["Keyslots"]["1"]["Key"] == "512 bits"
    assert parsed_dict["Keyslots"]["1"]["Priority"] == "normal"
    assert parsed_dict["Keyslots"]["1"]["Cipher"] == "aes-xts-plain64"
    assert parsed_dict["Keyslots"]["1"]["Cipher key"] == "512 bits"
    assert parsed_dict["Keyslots"]["1"]["PBKDF"] == "pbkdf2"
    assert parsed_dict["Keyslots"]["1"]["Hash"] == "sha256"
    assert parsed_dict["Keyslots"]["1"]["Iterations"] == "1000"
    assert parsed_dict["Keyslots"]["1"]["Salt"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Keyslots"]["1"]["AF stripes"] == "4000"
    assert parsed_dict["Keyslots"]["1"]["AF hash"] == "sha256"
    assert parsed_dict["Keyslots"]["1"]["Area offset"] == "290816 [bytes]"
    assert parsed_dict["Keyslots"]["1"]["Area length"] == "258048 [bytes]"
    assert parsed_dict["Keyslots"]["1"]["Digest ID"] == "0"

    assert parsed_dict["Keyslots"]["2"]["type"] == "luks2"
    assert parsed_dict["Keyslots"]["2"]["Key"] == "512 bits"
    assert parsed_dict["Keyslots"]["2"]["Priority"] == "normal"
    assert parsed_dict["Keyslots"]["2"]["Cipher"] == "aes-xts-plain64"
    assert parsed_dict["Keyslots"]["2"]["Cipher key"] == "512 bits"
    assert parsed_dict["Keyslots"]["2"]["PBKDF"] == "pbkdf2"
    assert parsed_dict["Keyslots"]["2"]["Hash"] == "sha256"
    assert parsed_dict["Keyslots"]["2"]["Iterations"] == "1000"
    assert parsed_dict["Keyslots"]["2"]["Salt"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Keyslots"]["2"]["AF stripes"] == "4000"
    assert parsed_dict["Keyslots"]["2"]["AF hash"] == "sha256"
    assert parsed_dict["Keyslots"]["2"]["Area offset"] == "548864 [bytes]"
    assert parsed_dict["Keyslots"]["2"]["Area length"] == "258048 [bytes]"
    assert parsed_dict["Keyslots"]["2"]["Digest ID"] == "0"

    assert parsed_dict["Keyslots"]["3"]["type"] == "luks2"
    assert parsed_dict["Keyslots"]["3"]["Key"] == "512 bits"
    assert parsed_dict["Keyslots"]["3"]["Priority"] == "normal"
    assert parsed_dict["Keyslots"]["3"]["Cipher"] == "aes-xts-plain64"
    assert parsed_dict["Keyslots"]["3"]["Cipher key"] == "512 bits"
    assert parsed_dict["Keyslots"]["3"]["PBKDF"] == "pbkdf2"
    assert parsed_dict["Keyslots"]["3"]["Hash"] == "sha512"
    assert parsed_dict["Keyslots"]["3"]["Iterations"] == "1000"
    assert parsed_dict["Keyslots"]["3"]["Salt"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Keyslots"]["3"]["AF stripes"] == "4000"
    assert parsed_dict["Keyslots"]["3"]["AF hash"] == "sha512"
    assert parsed_dict["Keyslots"]["3"]["Area offset"] == "806912 [bytes]"
    assert parsed_dict["Keyslots"]["3"]["Area length"] == "258048 [bytes]"
    assert parsed_dict["Keyslots"]["3"]["Digest ID"] == "0"

    assert len(parsed_dict["Tokens"]) == 3
    assert parsed_dict["Tokens"]["0"]["type"] == "clevis"
    assert parsed_dict["Tokens"]["0"]["Keyslot"] == "1"

    assert parsed_dict["Tokens"]["1"]["type"] == "clevis"
    assert parsed_dict["Tokens"]["1"]["Keyslot"] == "2"

    assert parsed_dict["Tokens"]["2"]["type"] == "systemd-tpm2"
    assert parsed_dict["Tokens"]["2"]["Keyslot"] == "3"
    assert parsed_dict["Tokens"]["2"]["tpm2-hash-pcrs"] == "7"
    assert parsed_dict["Tokens"]["2"]["tpm2-pcr-bank"] == "sha256"
    assert parsed_dict["Tokens"]["2"]["tpm2-pubkey"] == "(null)"
    assert parsed_dict["Tokens"]["2"]["tpm2-pubkey-pcrs"] == "n/a"
    assert parsed_dict["Tokens"]["2"]["tpm2-primary-alg"] == "ecc"
    assert parsed_dict["Tokens"]["2"]["tpm2-blob"].replace(" ", "") == 14*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Tokens"]["2"]["tpm2-policy-hash"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Tokens"]["2"]["tpm2-pin"] == "false"
    assert parsed_dict["Tokens"]["2"]["tpm2-salt"] == "false"

    assert len(parsed_dict["Digests"]) == 1
    assert parsed_dict["Digests"]["0"]["type"] == "pbkdf2"
    assert parsed_dict["Digests"]["0"]["Hash"] == "sha256"
    assert parsed_dict["Digests"]["0"]["Iterations"] == "117448"
    assert parsed_dict["Digests"]["0"]["Salt"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
    assert parsed_dict["Digests"]["0"]["Digest"].replace(" ", "") == 2*"dea1b97f03cbb489e25220fce42465cd"
