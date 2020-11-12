from leapp.models import InstalledDesktopsFacts, InstalledKdeAppsFacts, Report


no_desktop_env = InstalledDesktopsFacts(gnome_installed=False,
                                        kde_installed=False)
gnome_desktop_env = InstalledDesktopsFacts(gnome_installed=True,
                                           kde_installed=False)
KDE_desktop_env = InstalledDesktopsFacts(gnome_installed=False,
                                         kde_installed=True)
both_desktop_env = InstalledDesktopsFacts(gnome_installed=True,
                                          kde_installed=True)


no_KDE_apps = InstalledKdeAppsFacts(installed_apps=[])
some_KDE_apps = InstalledKdeAppsFacts(installed_apps=["okular", "kate"])


def test_no_desktop_no_apps(current_actor_context):
    """
    No action expected.
    """
    current_actor_context.feed(no_desktop_env)
    current_actor_context.feed(no_KDE_apps)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_gnome_desktop_no_apps(current_actor_context):
    """
    No action expected.
    """
    current_actor_context.feed(gnome_desktop_env)
    current_actor_context.feed(no_KDE_apps)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_gnome_desktop_KDE_apps(current_actor_context):
    """
    One report about deleting KDE apps expected.
    """
    current_actor_context.feed(gnome_desktop_env)
    current_actor_context.feed(some_KDE_apps)
    current_actor_context.run()
    message = current_actor_context.consume(Report)[0]
    assert "Upgrade can be performed, but KDE/Qt apps will be uninstalled." in message.report["title"]


def test_KDE_desktop_no_apps(current_actor_context):
    """
    "Inhibitor" group in report expected.
    """
    current_actor_context.feed(KDE_desktop_env)
    current_actor_context.feed(no_KDE_apps)
    current_actor_context.run()
    message = current_actor_context.consume(Report)[0]
    assert "inhibitor" in message.report["groups"]


def test_KDE_desktop_KDE_apps(current_actor_context):
    """
    "Inhibitor" group in report expected.
    """
    current_actor_context.feed(KDE_desktop_env)
    current_actor_context.feed(some_KDE_apps)
    current_actor_context.run()
    message = current_actor_context.consume(Report)[0]
    assert "inhibitor" in message.report["groups"]


def test_both_desktops_no_apps(current_actor_context):
    """
    Report about removing KDE desktop environment expected.
    """
    current_actor_context.feed(both_desktop_env)
    current_actor_context.feed(no_KDE_apps)
    current_actor_context.run()
    message = current_actor_context.consume(Report)[0]
    assert "Upgrade can be performed, but KDE will be uninstalled." in message.report["title"]


def test_both_desktop_KDE_apps(current_actor_context):
    """
    Two reports expected, first about removing KDE desktop, second about KDE/Qt apps
    """
    current_actor_context.feed(both_desktop_env)
    current_actor_context.feed(some_KDE_apps)
    current_actor_context.run()
    messages = current_actor_context.consume(Report)
    remove_KDE_title = "Upgrade can be performed, but KDE will be uninstalled."
    remove_apps_title = "Upgrade can be performed, but KDE/Qt apps will be uninstalled."
    assert len(messages) == 2
    assert [True for message in messages if remove_KDE_title in message.report["title"]]
    assert [True for message in messages if remove_apps_title in message.report["title"]]
