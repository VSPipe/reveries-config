
import os
import shutil
import pyblish.api
from collections import OrderedDict


def to_tx(path):
    return os.path.splitext(path)[0] + ".tx"


class ExtractTexture(pyblish.api.InstancePlugin):
    """Export texture files
    """

    label = "Extract Texture"
    order = pyblish.api.ExtractorOrder - 0.1  # Run before look extractor
    hosts = ["maya"]
    families = ["reveries.texture"]

    def process(self, instance):
        import avalon.api
        import avalon.io
        from reveries import lib, utils
        from reveries.maya import plugins, lib as maya_lib

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        published_dir = self.published_dir(instance)

        file_inventory = list()
        NEW_OR_CHANGED = list()

        PREVIOUS = dict()
        CURRENT = dict()

        USE_TX = instance.data.get("useTxMaps", False)
        files_to_tx = dict()
        files_to_copy = dict()

        # Get previous files
        path = [
            avalon.api.Session["AVALON_PROJECT"],
            avalon.api.Session["AVALON_ASSET"],
            instance.data["subset"],
            -1,  # latest version
            "TexturePack"
        ]
        representation_id = avalon.io.locate(path)
        if representation_id is not None:
            repr = avalon.io.find_one({"_id": representation_id})

            file_inventory = repr["data"].get("fileInventory", [])
            PREVIOUS = maya_lib.resolve_file_profile(repr, file_inventory)

        # Get current files
        for data in instance.data["fileData"]:
            file_node = data["node"]
            if file_node in instance.data["fileNodesToIgnore"]:
                continue

            dir_name = data["dir"]
            fnames = data["fnames"]
            fpattern = data["fpattern"]

            CURRENT[fpattern] = {
                "node": data["node"],
                "colorSpace": data["colorSpace"],
                "fnames": fnames,
                "pathMap": {fn: dir_name + "/" + fn for fn in fnames},
            }

        # Extract textures
        #
        self.log.info("Extracting textures..")

        # For storing calculated published file path for look or lightSet
        # extractors to update file path.
        if "fileNodeAttrs" not in instance.data:
            instance.data["fileNodeAttrs"] = OrderedDict()

        # To transfer
        #
        new_version = instance.data["versionNext"]

        for fpattern, data in CURRENT.items():
            if not data["fnames"]:
                raise RuntimeError("Empty file list, this is a bug.")

            file_nodes = [dat["node"] for dat in instance.data["fileData"]
                          if dat["fpattern"] == fpattern]

            versioned_data = PREVIOUS.get(fpattern, list())
            versioned_data.sort(key=lambda elem: elem[0]["version"],
                                reverse=True)  # elem: (data, tmp_data)

            current_color_space = data["colorSpace"]

            for ver_data, tmp_data in versioned_data:

                previous_files = tmp_data["pathMap"]

                all_files = list()
                for file, abs_path in data["pathMap"].items():
                    if file not in previous_files:
                        # Possible different file pattern
                        break  # Try previous version

                    abs_previous = previous_files.get(file, "")

                    if not os.path.isfile(abs_previous):
                        # Previous file not exists (should not happen)
                        break  # Try previous version

                    # Checking on file size and modification time
                    same_file = lib.file_cmp(abs_path, abs_previous)
                    if not same_file:
                        # Possible new files
                        break  # Try previous version

                    all_files.append(file)

                else:
                    # Version matched, consider as same file
                    head_file = sorted(all_files)[0]
                    resolved_path = abs_previous[:-len(file)] + head_file
                    resolved_path = plugins.env_embedded_path(resolved_path)
                    self.update_file_node_attrs(instance,
                                                file_nodes,
                                                resolved_path,
                                                current_color_space)
                    # Update color space
                    # * Although files may be the same, but color space may
                    #   changed by artist.
                    # * We only keep track the color space, not apply them
                    #   from database.
                    ver_data["colorSpace"] = current_color_space

                    # Proceed to next pattern
                    break

            else:
                # Not match with any previous version, consider as new file
                self.log.info("New texture collected from '%s': %s"
                              "" % (data["node"], fpattern))

                NEW_OR_CHANGED.append({
                    "fpattern": fpattern,
                    "version": new_version,
                    "colorSpace": current_color_space,
                    "fnames": data["fnames"],
                })

                all_files = list()
                for file, abs_path in data["pathMap"].items():

                    files_to_copy[file] = abs_path

                    if USE_TX:
                        # Upload .tx file as well
                        tx_abs_path = to_tx(abs_path)
                        tx_stage_file = to_tx(file)

                        if current_color_space == "Raw":
                            input_colorspace = "linear"
                        else:
                            input_colorspace = current_color_space

                        files_to_copy[tx_stage_file] = tx_abs_path
                        files_to_tx[tx_abs_path] = (abs_path,
                                                    input_colorspace)

                    all_files.append(file)

                head_file = sorted(all_files)[0]
                resolved_path = published_dir + "/" + head_file
                self.update_file_node_attrs(instance,
                                            file_nodes,
                                            resolved_path,
                                            current_color_space)

        file_inventory += NEW_OR_CHANGED

        instance.data["maketx"] = files_to_tx

        instance.data["repr.TexturePack._stage"] = staging_dir
        instance.data["repr.TexturePack._hardlinks"] = list(files_to_copy)
        instance.data["repr.TexturePack.fileInventory"] = file_inventory

        # (NOTE) We need to delay extract textrues is because the texture
        #   instance could be a child instance of `reveries.standin`, and
        #   a standin could be extracted in Deadline so the extraction of
        #   the child should be there, too.
        #
        #   But a standin could also be extracted in sequential Deadline
        #   tasks, which isn't fit for extracting it's textures.
        #
        #   So we extract it here in local, and put a mock function which
        #   will do nothing when the Deadline extraction script runs in
        #   each tasks.
        #
        instance.data["repr.TexturePack._delayRun"] = {
            "func": self.mock_stage,
        }
        self.stage_textures(staging_dir, files_to_copy)

    def update_file_node_attrs(self, instance, file_nodes, path, color_space):
        # (NOTE) All input `file_nodes` will be set to same `color_space`
        from reveries.maya import lib

        for node in file_nodes:
            attr = node + ".fileTextureName"
            instance.data["fileNodeAttrs"][attr] = path
            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            attr = node + ".colorSpace"
            instance.data["fileNodeAttrs"][attr] = color_space

            attr = node + ".ignoreColorSpaceFileRules"
            instance.data["fileNodeAttrs"][attr] = True

            if lib.hasAttr(node, "aiAutoTx"):
                # Although we ensured the tx update, but the file modification
                # time still may loose during file transfer and trigger another
                # tx update later on. So we force disable it on each published
                # file node.
                attr = node + ".aiAutoTx"
                instance.data["fileNodeAttrs"][attr] = False

    def published_dir(self, instance):
        from reveries.maya import plugins

        template_publish = instance.data["publishPathTemplate"]
        template_data = instance.data["publishPathTemplateData"]
        published_dir = template_publish.format(representation="TexturePack",
                                                **template_data)
        if not os.path.isdir(published_dir):
            # Ensure dir exists, even no new or changed texture files
            os.makedirs(published_dir)

        return plugins.env_embedded_path(published_dir)

    def stage_textures(self, staging_dir, files_to_copy):
        for file, src in files_to_copy.items():

            dst = staging_dir + "/" + file

            dst_dir = os.path.dirname(dst)
            if not os.path.isdir(dst_dir):
                os.makedirs(dst_dir)

            try:
                self.log.info("Staging %s" % src)
                shutil.copy2(src, dst)
            except OSError:
                msg = "An unexpected error occurred."
                self.log.critical(msg)
                raise OSError(msg)

    def mock_stage(self, *args, **kwargs):
        # Do nothing, texture files should already been staged by now.
        pass
