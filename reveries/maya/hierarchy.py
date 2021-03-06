
import contextlib
import logging
import avalon.io
from collections import OrderedDict

from maya import cmds
from avalon.maya.pipeline import (
    AVALON_CONTAINER_ID,
    AVALON_CONTAINERS,
)

from ..plugins import message_box_error

from . import lib
from . import capsule
from .pipeline import parse_container


_log = logging.getLogger("reveries.maya.hierarchy")


def get_sub_container_nodes(container):
    """Get the Avalon containers in this container (node only)

    Args:
        container (dict): The container dict.

    Returns:
        list: A list of child container node names.

    """
    containers = []

    for node in cmds.ls(cmds.sets(container["objectName"], query=True),
                        type="objectSet"):
        id = node + ".id"
        if not cmds.objExists(id):
            continue
        if not cmds.getAttr(id) == AVALON_CONTAINER_ID:
            continue
        containers.append(node)

    return containers


def parse_sub_containers(container):
    """Get the Avalon containers in this container

    Args:
        container (dict): The container dict.

    Returns:
        list: A list of member container dictionaries.

    """
    containers = []

    for node in get_sub_container_nodes(container):
        containers.append(parse_container(node))

    return containers


def walk_containers(container):
    """Recursively yield input container's sub-containers

    Args:
        container (dict): The container dict.

    Yields:
        dict: sub-container

    """
    for con in parse_sub_containers(container):
        yield con
        for sub_con in walk_containers(con):
            yield sub_con


def climb_container_id(container):
    """Recursively yield container ID from buttom(leaf) to top(root)

    Args:
        container (str): The container node name

    Yields:
        str: container id

    """
    parents = cmds.ls(cmds.listSets(object=container), type="objectSet")
    for m in parents:
        # Find container node
        if (lib.hasAttr(m, "id") and
                cmds.getAttr(m + ".id") == AVALON_CONTAINER_ID):

            yield cmds.getAttr(m + ".containerId")
            # Next parent
            for n in climb_container_id(m):
                yield n


def walk_container_id(container):
    """Recursively yield container ID from top(root) to buttom(leaf)

    Args:
        container (str): The container node name

    Yields:
        str: container id

    """
    parents = cmds.ls(cmds.listSets(object=container), type="objectSet")
    for m in parents:
        # Find container node
        if (lib.hasAttr(m, "id") and
                cmds.getAttr(m + ".id") == AVALON_CONTAINER_ID):
            # Find next parent before yielding `containerId`
            for n in walk_container_id(m):
                yield n

    yield cmds.getAttr(container + ".containerId")


def container_to_id_path(container):
    """Return the id path of the container

    Args:
        container (dict): The container dict.

    Returns:
        str: container id path

    """
    return "|".join(walk_container_id(container["objectName"]))


_cached_container_by_id = {"_": None}


class UpwardContainerCache(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.cache = dict()

    def get(self, id):
        return self.cache.get(id, [])

    def add(self, id, node):
        if id not in self.cache:
            self.cache[id] = set()
        self.cache[id].add(node)

        if self.parent is not None:
            # Pass new node into parent loader's cache, so the parent loader
            # can access the node from it's cache when overriding variations
            # there, after this loader is finished loading and cache removed.
            self.parent.add(id, node)

    def remove(self, id, node):
        self.cache[id].remove(node)


def cache_container_by_id(plugin, add=None, remove=None, update=None):
    if add:
        container = add
        id = container["containerId"]
        node = ":" + container["objectName"]
        container_by_id = plugin._cache
        container_by_id.add(id, node)

        return

    elif remove:
        id, node = remove
        container_by_id = plugin._cache
        container_by_id.remove(id, node)

        return

    # Init cache
    parent = plugin._parent
    container_by_id = UpwardContainerCache(None if parent is None
                                           else parent._cache)

    if update:
        namespace = update

        for attr in lib.lsAttr("containerId", namespace=namespace + "::"):
            id = cmds.getAttr(attr)
            node = ":" + attr.rsplit(".", 1)[0]
            container_by_id.add(id, node)

    plugin._cache = container_by_id


def container_from_id_path(plugin, container_id_path, parent_namespace):
    """Find container node from container id path

    Args:
        container_id_path (str): The container id path
        parent_namespace (str): Namespace

    Returns:
        (str, None): container node name, return None if not found

    """
    container_ids = container_id_path.split("|")
    container_by_id = plugin._cache

    leaf_id = container_ids.pop()  # leaf container id

    if container_by_id is None:
        leaf_containers = lib.lsAttr("containerId",
                                     leaf_id,
                                     parent_namespace + "::")
    else:
        leaf_containers = [
            node for node in
            container_by_id.get(leaf_id)
            if node.startswith(parent_namespace + ":")
        ]

    if not leaf_containers:
        message = ("No leaf containers with Id %s under namespace %s, "
                   "possibly been removed in parent asset.")
        _log.debug(message % (container_id_path, parent_namespace))

        return None

    walkers = OrderedDict([(leaf, climb_container_id(leaf))
                           for leaf in leaf_containers])

    while container_ids:
        con_id = container_ids.pop()
        next_walkers = OrderedDict()

        for leaf, walker in walkers.items():
            _id = next(walker)
            if con_id == _id:
                next_walkers[leaf] = walker

        walkers = next_walkers

        if len(walkers) == 1:
            break

    if not len(walkers):
        _log.debug("Container Id %s not found under namespace %s, possibly "
                   "been removed." % (container_id_path, parent_namespace))
        return None

    elif len(walkers) > 1:
        cmds.warning("Container Id %s not unique under namespace %s, "
                     "this is a bug." % (container_id_path, parent_namespace))
        # (NOTE) This shuold have been resolved in this commit, but just in
        #        case and take a wild guess.
        container = next(reversed(walkers.keys()))
    else:
        container = next(iter(walkers.keys()))

    # Remove resolved container from cache
    cache_container_by_id(plugin, remove=(leaf_id, container))

    return container


_cached_representations = dict()


def get_representation(representation_id):
    """
    """
    try:

        return _cached_representations[representation_id]

    except KeyError:
        representation = avalon.io.find_one(
            {"_id": avalon.io.ObjectId(representation_id)})

        if representation is None:
            raise RuntimeError("Representation not found, this is a bug.")

        _cached_representations[representation_id] = representation

        return representation


_cached_loaders = dict()


def get_loader(loader_name, representation_id):
    """
    """
    try:

        return _cached_loaders[representation_id]

    except KeyError:
        # Get all loaders
        all_loaders = avalon.api.discover(avalon.api.Loader)
        # Find the compatible loaders
        loaders = avalon.api.loaders_from_representation(
            all_loaders, get_representation(representation_id))
        # Get the used loader
        Loader = next((x for x in loaders if
                       x.__name__ == loader_name),
                      None)

        if Loader is None:
            raise RuntimeError("Loader is missing: %s", loader_name)

        _cached_loaders[representation_id] = Loader

        return Loader


def _attach_subset(slot, namespace, root, subset_group):
    """Attach into the setdress hierarchy
    """
    # Namespace is missing from root node(s), add namespace
    # manually
    slot = lib.to_namespace(slot, namespace)
    slot = cmds.ls(root + slot)

    if not len(slot) == 1:
        raise RuntimeError("Too many or no parent, this is a bug.")

    slot = slot[0]
    current_parent = cmds.listRelatives(subset_group,
                                        parent=True,
                                        path=True) or []
    if slot not in current_parent:
        subset_group = cmds.parent(subset_group, slot, relative=True)[0]

    return subset_group


@contextlib.contextmanager
def add_subset(data, namespace, root, on_update=None):
    """
    """
    if data["namespace"]:
        sub_namespace = namespace + ":" + data["namespace"]
    else:
        sub_namespace = namespace

    options = {
        "containerId": data["containerId"],
        "hierarchy": data["hierarchy"],
        "_parent": data.pop("_parent", None),
    }

    sub_container = avalon.api.load(data["loaderCls"],
                                    data["representationDoc"],
                                    namespace=sub_namespace,
                                    options=options)
    subset_group = sub_container["subsetGroup"]

    try:

        with capsule.namespaced(namespace, new=False) as namespace:
            subset_group = _attach_subset(data["slot"],
                                          namespace,
                                          root,
                                          subset_group)
            sub_container["subsetGroup"] = subset_group

            yield sub_container

    finally:

        if on_update is None:
            cmds.sets(sub_container["objectName"], remove=AVALON_CONTAINERS)
        else:
            container = on_update
            cmds.sets(sub_container["objectName"],
                      forceElement=container["objectName"])


def get_updatable_containers(container):
    """Get sub-containers and ensure they are updatable
    """
    updatable_import_loaders = (
        "ArnoldAssLoader",
        "AnimationLoader",
        "ArnoldVolumeLoader",
        "AtomsCrowdCacheLoader",
    )

    def get_ref_node(node):
        """Find one reference node in the members of objectSet"""
        members = cmds.sets(node, query=True)
        return next(iter(lib.get_reference_nodes(members)), None)

    def abort_alert(name):
        """Error message box"""
        title = "Abort"
        message = ("Found not updatable child subset %s, abort." % name)
        _log.error(message)
        message_box_error(title, message)

        raise RuntimeError(message)

    # Get current sub-containers
    current_subcons = dict()

    for sub_con in parse_sub_containers(container):
        if not get_ref_node(sub_con["objectName"]):
            loader = sub_con["loader"]
            if loader not in updatable_import_loaders:
                abort_alert(sub_con["objectName"])

        sub_ns = sub_con["namespace"].rsplit(":", 1)[-1]
        current_subcons[sub_ns] = sub_con

    return current_subcons


@contextlib.contextmanager
def change_subset(container, namespace, root, data_new, data_old, force):
    """
    """
    from avalon.pipeline import get_representation_context

    container["_parent"] = data_new.pop("_parent", None)
    container["_force_update"] = force

    hierarchical_loaders = [
        "SetDressLoader",
    ]

    require_update = (
        data_new["representation"] != container["representation"]
        or container["loader"] in hierarchical_loaders
    )
    is_updatable = (
        data_old["representation"] == container["representation"]
        or force
    )

    # Update representation or not
    if require_update and is_updatable:
        current_repr = get_representation_context(container["representation"])
        loader = data_new["loaderCls"](current_repr)
        loader.update(container, data_new["representationDoc"])
    else:
        # No need or could not update
        pass

    try:
        # Update subset group's parenting and matrix
        with capsule.namespaced(namespace, new=False) as namespace:
            subset_group = _attach_subset(data_new["slot"],
                                          namespace,
                                          root,
                                          container["subsetGroup"])
            container["subsetGroup"] = subset_group

            yield container

    finally:
        pass
