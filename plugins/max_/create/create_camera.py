
import sys
import avalon

class CameraCreator(avalon.max_.Creator):
    """發佈攝影機, 請選取攝影機主體"""

    label = "Camera"
    family = "reveries.camera"
    icon = "video-camera"

    def process(self):
        return super(CameraCreator, self).process()
