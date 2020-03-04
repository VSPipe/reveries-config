'''
Created on 2020-02-26

@author: noflame.lin
'''

import pyblish.api
import MaxPlus as MP

class CollectWorkFileName(pyblish.api.ContextPlugin):
    """紀錄當前工作檔的檔案路徑"""
    label = "當前工作檔"
    order = pyblish.api.CollectorOrder - 0.05
    hosts = ["max_"]

    def process(self, context):
        val = MP.Core_EvalMAXScript('maxfilename').Get()
        if val == '':
            context.data['currentMaking'] = val
        else:
            context.data['currentMaking'] = MP.Core_EvalMAXScript('maxfilepath').Get() + val
        self.log.info("maxfile: %s" % context.data["currentMaking"])