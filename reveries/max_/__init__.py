import os

try:
    import MaxPlus as MP
    import pymxs
except ImportError:
    raise ImportError("Module 'reveries.max_' require Autodesk 3dsMax.")

from .. import PLUGINS_DIR
import avalon.api as avalon
from pyblish import api as pyblish


# try:
#     from . import pipeline
# except:
#     print("ERROR: from . import pipeline")
# 
# try:
#     from .pipeline import install
# except:
#     print("ERROR: from .pipeline import install")

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