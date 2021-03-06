
import logging
from avalon import io
from avalon.vendor import qtawesome
from avalon.tools import lib, delegates
from ... import lib as reveries_lib


main_logger = logging.getLogger("modeldiffer")


schedule = lib.schedule
defer = lib.defer


def avalon_id_pretty_time(id):
    timestamp = reveries_lib.avalon_id_timestamp(id)
    return delegates.pretty_timestamp(timestamp)


def icon(name, color=None):
    return qtawesome.icon("fa.{}".format(name), color=color)


def profile_from_database(version_id):
    """
    """
    representation = io.find_one({"type": "representation",
                                  "name": "mayaBinary",
                                  "parent": version_id})
    if representation is None:
        main_logger.critical("Representation not found. This is a bug.")
        return

    model_profile = representation["data"].get("modelProfile")
    model_protected = representation["data"].get("modelProtected", [])

    if model_profile is None:
        main_logger.critical("'data.modelProfile' not found."
                             "This is a bug.")
        return

    profile = dict()

    for id, meshes in model_profile.items():
        # Currently, meshes with duplicated id are not supported,
        # and may remain unsupported in the future.
        data = meshes[0]

        name = data.pop("hierarchy")
        # No need to compare normals
        data.pop("normals")

        data["avalonId"] = id
        data["protected"] = id in model_protected

        profile[name] = data

    return profile


profile_from_host = NotImplemented
select_from_host = NotImplemented


def is_supported_loader(name):
    return name in ("ModelLoader",)  # "RigLoader")


def is_supported_subset(name):
    return any(name.startswith(family)
               for family in ("model",))  # "rig"))
