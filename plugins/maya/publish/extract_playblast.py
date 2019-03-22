
import os
import pyblish.api
import reveries.utils

from avalon.vendor import clique
from reveries.maya import io, utils
from reveries.plugins import DelegatablePackageExtractor, skip_stage


class ExtractPlayblast(DelegatablePackageExtractor):
    """
    """

    label = "Extract Playblast"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]

    families = [
        "reveries.imgseq.playblast",
    ]

    representations = [
        "imageSequence"
    ]

    ext = "png"

    @skip_stage
    def extract_imageSequence(self):
        """Extract playblast sequence directly to publish dir
        """
        from maya import cmds
        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        project = self.context.data["projectDoc"]
        width, height = reveries.utils.get_resolution_data(project)
        e_in, e_out, handles, _ = reveries.utils.get_timeline_data(project)

        start_frame = self.context.data["startFrame"]
        end_frame = self.context.data["endFrame"]

        entry_file = self.file_name()
        publish_dir = self.create_package()
        entry_path = os.path.join(publish_dir, entry_file)

        camera = self.data["renderCam"][0]
        io.capture_seq(camera,
                       entry_path,
                       start_frame,
                       end_frame,
                       width,
                       height)

        # Check image sequence length to ensure that the extraction did
        # not interrupted.
        files = os.listdir(publish_dir)
        collections, _ = clique.assemble(files)

        assert len(collections), "Extraction failed, no sequence found."

        sequence = collections[0]

        entry_fname = (sequence.head +
                       "%%0%dd" % sequence.padding +
                       sequence.tail)

        self.add_data({
            "imageFormat": self.ext,
            "entryFileName": entry_fname,
            "seqStart": list(sequence.indexes)[0],
            "seqEnd": list(sequence.indexes)[-1],
            "startFrame": start_frame,
            "endFrame": end_frame,
            "byFrameStep": 1,
            "edit_in": e_in,
            "edit_out": e_out,
            "handles": handles,
            "focalLength": cmds.getAttr(camera + ".focalLength"),
            "resolution": (width, height),
            "fps": self.context.data["fps"],
            "cameraUUID": utils.get_id(camera),
        })
