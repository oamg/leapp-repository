from leapp.models import GrubConfigError, Report
from leapp.utils import report

grub_cmdline_syntax_error = GrubConfigError(error_type=GrubConfigError.ERROR_GRUB_CMDLINE_LINUX_SYNTAX,
                                            files=['/etc/default/grub.cfg'])
grub_cmdline_syntax_error2 = GrubConfigError(error_type=GrubConfigError.ERROR_GRUB_CMDLINE_LINUX_SYNTAX,
                                             files=['/boot/grub2/grub.cfg', '/etc/default/someothergrub.cfg'])

grub_missing_newline_error = GrubConfigError(error_type=GrubConfigError.ERROR_MISSING_NEWLINE,
                                             files=['/etc/default/someothergrub.cfg'])
grub_missing_newline_error2 = GrubConfigError(error_type=GrubConfigError.ERROR_MISSING_NEWLINE,
                                              files=['/etc/default/grub'])

grub_corrupted_config = GrubConfigError(error_type=GrubConfigError.ERROR_CORRUPTED_GRUBENV,
                                        files=['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg'])
grub_corrupted_config2 = GrubConfigError(error_type=GrubConfigError.ERROR_CORRUPTED_GRUBENV,
                                         files=['/boot/grub2/grub.cfg'])


def test_cmdline_syntax_error(current_actor_context):
    # Make sure that just 1 low priority report message is created with config files present.
    current_actor_context.feed(grub_cmdline_syntax_error)
    current_actor_context.feed(grub_cmdline_syntax_error2)
    current_actor_context.run()
    messages = current_actor_context.consume(Report)
    assert len(messages) == 1
    message = messages[0]
    assert 'Syntax error detected in grub configuration' in message.report['title']
    assert message.report['severity'] == 'low'
    assert message.report['detail']['related_resources'][0]['title'] == '/etc/default/grub.cfg'


def test_missing_newline(current_actor_context):
    # Make sure that just 1 low priority report message is created with config files present
    current_actor_context.feed(grub_missing_newline_error)
    current_actor_context.feed(grub_missing_newline_error2)
    current_actor_context.run()
    messages = current_actor_context.consume(Report)
    assert len(messages) == 1
    message = messages[0]
    assert 'Detected a missing newline at the end of grub configuration file' in message.report['title']
    assert message.report['severity'] == 'low'
    assert message.report['detail']['related_resources'][0]['title'] == '/etc/default/someothergrub.cfg'


def test_corrupted_config(current_actor_context):
    # Make sure that just 1 high priority report message is created with config files present
    current_actor_context.feed(grub_corrupted_config)
    current_actor_context.feed(grub_corrupted_config2)
    current_actor_context.run()
    messages = current_actor_context.consume(Report)
    assert len(messages) == 1
    message = messages[0]
    assert 'Detected a corrupted grubenv file' in message.report['title']
    assert message.report['severity'] == 'high'
    assert message.report['detail']['related_resources'][0]['title'] == '/boot/grub2/grub.cfg'
    assert message.report['detail']['related_resources'][1]['title'] == '/boot/efi/EFI/redhat/grub.cfg'
    assert report.is_inhibitor(message.report)
