import os
from .. import PLUGINS_DIR
import avalon.api as avalon

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "max_", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "max_", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "max_", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "max_", "inventory")


def install():
    print('Install MoonShine Avalaon Setting...')
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

def unistall():
    print('Uninstall MoonShine Avalaon Setting...')
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)