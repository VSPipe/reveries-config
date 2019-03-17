
import os
import importlib
from maya import cmds, OpenMaya
from avalon import maya, api as avalon

from .. import utils
from .pipeline import set_scene_timeline
from .vendor import sticker

from . import PYMEL_MOCK_FLAG, utils as maya_utils


def on_task_changed(_, *args):
    avalon.logger.info("Changing Task module..")

    utils.init_app_workdir()
    maya.pipeline._on_task_changed()

    if not cmds.file(query=True, sceneName=True):
        set_scene_timeline()


def on_init(_):
    if os.path.isfile(PYMEL_MOCK_FLAG):
        avalon.logger.info("Mocking PyMel..")
        importlib.import_module("reveries.maya.vendor.pymel_mock")

    avalon.logger.info("Running callback on init..")
    cmds.loadPlugin("AbcImport", quiet=True)
    cmds.loadPlugin("AbcExport", quiet=True)
    cmds.loadPlugin("fbxmaya", quiet=True)

    avalon.logger.info("Installing callbacks on import..")

    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterImport,
        on_import
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeImport,
        before_import
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterImportReference,
        on_import_reference
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeImportReference,
        before_import_reference
    )


def on_new(_):
    try:
        set_scene_timeline()
    except Exception as e:
        cmds.warning(e.message)


def on_open(_):
    sticker.reveal()  # Show custom icon


def on_save(_):
    avalon.logger.info("Running callback on save..")


def before_save(return_code, _):
    """Prevent accidental overwrite of locked scene"""

    # Manually override message given by default dialog
    # Tested with Maya 2013-2017
    dialog_id = "s_TfileIOStrings.rFileOpCancelledByUser"
    message = ("Scene is locked, please save under a new name.")
    cmds.displayString(dialog_id, replace=True, value=message)

    # Returning false in C++ causes this to abort a save in-progress,
    # but that doesn't translate from Python. Instead, the `setBool`
    # is used to mimic this beahvior.
    # Docs: http://download.autodesk.com/us/maya/2011help/api/
    # class_m_scene_message.html#a6bf4288015fa7dab2d2074c3a49f936
    OpenMaya.MScriptUtil.setBool(return_code, not maya.is_locked())


_nodes = {"_": None}


def before_import(_):
    avalon.logger.info("Running callback before import..")
    # Collect all nodes in scene
    _nodes["_"] = set(cmds.ls())


def on_import(_):
    avalon.logger.info("Running callback on import..")

    before_nodes = _nodes["_"]
    after_nodes = set(cmds.ls())

    imported_nodes = list(after_nodes - before_nodes)
    maya_utils.update_id_verifiers(imported_nodes)
    _nodes["_"] = None


def before_import_reference(_):
    avalon.logger.info("Running callback before import reference..")
    # Collect all referenced nodes in scene
    _nodes["_"] = set(cmds.ls(referencedNodes=True))


def on_import_reference(_):
    avalon.logger.info("Running callback on import reference..")

    before_nodes = _nodes["_"]
    after_nodes = set(cmds.ls(referencedNodes=True))

    imported_nodes = list(before_nodes - after_nodes)
    maya_utils.update_id_verifiers(imported_nodes)
    _nodes["_"] = None
