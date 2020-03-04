import pyblish.api


class CollectAvalonInstances(pyblish.api.ContextPlugin):
    """收集類別為 avalonSetHepler 的 個體

    This collector takes into account assets that are associated with
    a helper object and class of helper object is AvalonSet ;
    """

    order = pyblish.api.CollectorOrder - 0.3
    hosts = ["max_"]
    label = "找 Avalon Set"

    def process(self, context):
        import pymxs
        rt = pymxs.runtime
        
        targeted_families = context.data["targetFamilies"]
        objset_data = list()
 
        helpers = [obj for obj in rt.Helpers]        
        helpers = [helper for helper in helpers if rt.classOf(helper) == rt.AvalonSet]
        helpers = filter(lambda h: h.active , helpers)            
        # 找出 helper 並確認 helper 有  active
        if not helpers: return context
         
        for helper in helpers:
            if not helper.family:
                assert has_family, "\"%s\" was missing a family" % helper.name
            if not helper.avalon_nodes:
                self.log.warning("Skipped empty Helper: \"%s\" " % helper)
                continue
                # 排除未帶有物件的 helper
         
            # The developer is responsible for specifying
            # the family of each instance.
 
            data = dict()
            data["asset"] = helper.asset
            data["family"] = helper.family
            data['subset'] = helper.subset
            data["avaHelperName"] = helper.name
            data["setMembers"] = helper.avalon_nodes
 
            family = data["family"]
 
            # Ignore instance by targeted families
            families = set([family] + data.get("families", []))
            if not families.issubset(targeted_families):
                continue
 
            objset_data.append(data)
 
        # Sorting instances via using `data.publishOrder` as prim key
        ordering = (lambda data: (data.get("publishOrder", 0),
                                  data["family"],
                                  data["subset"],
                                  data["avaHelperName"],
                                  ))
 
        for data in sorted(objset_data, key=ordering):
            objset = data["avaHelperName"]
            members = data.pop("setMembers")
 
            # For dependency tracking
            data["dependencies"] = dict()
            data["futureDependencies"] = dict()
 
            # Create the instance
            self.log.info("Creating instance for {}".format(objset))
            instance = context.create_instance(data["subset"])
            #  instance[:] = cmds.ls(members, long=True)
            instance[:] = helper.avalon_nodes
            instance.data.update(data)
 
            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.name)

        return context
