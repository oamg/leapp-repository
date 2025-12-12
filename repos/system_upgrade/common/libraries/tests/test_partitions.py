import pytest
import re

from leapp.exceptions import StopActorExecution
from leapp.libraries.stdlib import CalledProcessError
from leapp.libraries.common import partitions


class RunMocked:

    def __init__(self, raise_err=False):
        self.called = 0
        self.args = None
        self.raise_err = raise_err

    def __call__(self, args, encoding=None, checked=True):
        self.called += 1
        self.args = args
        stdout = ""
        if self.raise_err:
            result = {
                "signal": None,
                "exit_code": 1,
                "pid": 0,
                "stdout": "fake",
                "stderr": "fake",
            }
            if checked is True:
                raise CalledProcessError(
                    message="A Leapp Command Error occurred.",
                    command=args,
                    result=result,
                )
            return result

        if self.args == ["grub2-probe", "--target=device", "/boot"]:
            stdout = "/dev/vda1"

        elif self.args[:-1] == ["lsblk", "-spnlo", "name"]:
            outputs = {
                "/dev/vda1": "/dev/vda",
                "/dev/vda8": "/dev/vda",
                "/dev/sdb1": "/dev/sdb",
                "/dev/sdb10": "/dev/sdb",
            }
            cmd_arg = self.args[-1]
            if cmd_arg in outputs:
                stdout = outputs[cmd_arg]
            else:
                # if the blk dev is not in the outputs above, let's treat it as
                # if it's not a partition, i.e. return it back
                assert not cmd_arg[:-1].isdigit()
                stdout = cmd_arg

        elif self.args[:-1] == ["/usr/sbin/blkid", "-p", "-s", "PART_ENTRY_NUMBER"]:
            partnum = re.search(r"\d+$", self.args[-1])
            if not partnum:
                stdout = "\n"
            else:
                stdout = 'PART_ENTRY_NUMBER="{}"'.format(partnum.group())
        else:
            assert False, "Called unexpected cmd not covered by test: {}".format(
                self.args
            )

        return {"stdout": stdout, "exit_code": 0}


@pytest.mark.parametrize(
    "partition,expect",
    [
        ("/dev/vda1", "/dev/vda"),
        ("/dev/vda8", "/dev/vda"),
        ("/dev/sdb1", "/dev/sdb"),
        ("/dev/sdb10", "/dev/sdb"),
        ("/dev/sdb", "/dev/sdb"),
        ("/dev/sda", "/dev/sda"),
    ],
)
def test_blk_dev_from_partition(monkeypatch, partition, expect):
    monkeypatch.setattr(partitions, "run", RunMocked())

    actual = partitions.blk_dev_from_partition(partition)
    assert actual == expect


def test_blk_dev_from_partition_fail(monkeypatch):
    monkeypatch.setattr(partitions, "run", RunMocked(raise_err=True))

    with pytest.raises(
        StopActorExecution, match="Could not get parent device of /dev/vda1 partition"
    ):
        partitions.blk_dev_from_partition("/dev/vda1")


@pytest.mark.parametrize(
    "partition,expect",
    [
        ("/dev/vda1", 1),
        ("/dev/vda8", 8),
        ("/dev/sdb1", 1),
        ("/dev/sdb10", 10),
    ],
)
def test_get_partition_number(monkeypatch, partition, expect):
    monkeypatch.setattr(partitions, "run", RunMocked())
    actual = partitions.get_partition_number(partition)
    assert actual == expect


def test_get_partition_number_not_a_partition(monkeypatch):
    monkeypatch.setattr(partitions, "run", RunMocked())

    dev = "/dev/vda"
    with pytest.raises(
        StopActorExecution, match="The {} device has no PART_ENTRY_NUMBER".format(dev)
    ):
        partitions.get_partition_number(dev)


def test_get_partition_number_fail(monkeypatch):
    monkeypatch.setattr(partitions, "run", RunMocked(raise_err=True))

    dev = "/dev/vda1"
    with pytest.raises(
        StopActorExecution,
        match="Unable to get information about the {} device".format(dev),
    ):
        partitions.get_partition_number(dev)


def test_get_partition_for_dir(monkeypatch):
    monkeypatch.setattr(partitions, "run", RunMocked())
    actual = partitions.get_partition_for_dir('/boot')
    assert actual == '/dev/vda1'


def test_get_partition_for_dir_command_missing(monkeypatch):

    def run_mocked(cmd, *args, **kwargs):
        assert cmd == ['grub2-probe', '--target=device', '/boot']
        raise OSError()

    monkeypatch.setattr(partitions, "run", run_mocked)

    msg = ('Could not get name of underlying /boot partition:'
        ' grub2-probe is missing.'
        ' Possibly called on system that does not use GRUB2?')
    with pytest.raises(StopActorExecution, match=msg):
        partitions.get_partition_for_dir('/boot')


def test_get_partition_for_dir_fail(monkeypatch):
    monkeypatch.setattr(partitions, "run", RunMocked(raise_err=True))

    msg = 'Could not get name of underlying /boot partition'
    with pytest.raises(StopActorExecution, match=msg):
        partitions.get_partition_for_dir('/boot')
