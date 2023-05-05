from leapp.models import XorgDrv, XorgDrvFacts
from leapp.reporting import Report


def test_actor_with_deprecated_driver(current_actor_context):
    for driver in ['RADEON', 'ATI', 'AMDGPU', 'MACH64', 'intel', 'spiceqxl', 'qxl', 'NOUVEAU', 'NV', 'VESA']:
        xorg_drv = [XorgDrv(driver=driver, has_options=False)]

        current_actor_context.feed(XorgDrvFacts(xorg_drivers=xorg_drv))
        current_actor_context.run()
        assert current_actor_context.consume(Report)


def test_actor_without_deprecated_driver(current_actor_context):
    xorg_drv = []

    current_actor_context.feed(XorgDrvFacts(xorg_drivers=xorg_drv))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
