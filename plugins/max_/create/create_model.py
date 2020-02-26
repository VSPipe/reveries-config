
import sys
import avalon

class ModelCreator(avalon.max_.Creator):
    """發佈模型, 請選取模型物件或群組"""

    label = "Model"
    family = "reveries.model"
    icon = "cubes"

    defaults = [
        "default",
        "polyHigh",
        "polyLow",
    ]

    def process(self):
        return super(ModelCreator, self).process()
