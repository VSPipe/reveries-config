
import pyblish.api
from reveries import plugins


class ValidateOutSetExcluded(pyblish.api.InstancePlugin):
    """Validate OutSet excluded meshes are safe to be excluded

    If a mesh is visible or the visibility is controllable (has connection),
    should be included in OutSet.

    """

    label = "Rig OutSet Excluded"
    order = pyblish.api.ValidatorOrder + 0.12
    hosts = ["maya"]

    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
    ]

    dependencies = [
        "ValidateRigContents",
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Visible meshes are not in OutSet.")

    @classmethod
    def get_excluded_meshes(cls, instance):
        from maya import cmds

        included = set()

        for out_set in instance.data["outSets"]:
            for node in cmds.sets(out_set, query=True) or []:
                shapes = cmds.listRelatives(node,
                                            shapes=True,
                                            noIntermediate=True,
                                            path=True)
                included.update(cmds.ls(shapes, type="mesh"))

        all_meshes = set(cmds.ls(instance,
                                 type="mesh",
                                 noIntermediate=True))
        excluded = all_meshes - included

        return list(excluded)

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya import lib

        invalid = list()

        if not plugins.depended_plugins_succeed(cls, instance):
            raise Exception("Depended plugin failed. See error log.")

        for mesh in cls.get_excluded_meshes(instance):
            node = cmds.listRelatives(mesh, parent=True, path=True)[0]

            if lib.is_visible(node,
                              displayLayer=False,
                              intermediateObject=False):
                invalid.append(node)

            elif cmds.listConnections(node + ".visibility",
                                      source=True,
                                      destination=False,
                                      connections=False):
                invalid.append(node)

        return invalid
