
from tomcru import TomcruProject, TomcruEnvCfg, TomcruSubProjectCfg, utils


class ServiceBase:
    INIT_PRIORITY = 1000

    def __init__(self, project: TomcruProject, cfg: utils.SettingWrapper, opts: utils.SettingWrapper, env: TomcruEnvCfg):
        self.p = project
        self.cfg = cfg
        self.env = env
        self.srvmgr = self.p.srvmgr
        self.opts = opts

    def service(self, name):
        return self.p.srvmgr.service(self.env, name)

    def object(self, serv, name):
        return self.p.objmgr.get(serv, name)

    def alias(self, name: str, serv_obj=None):
        if serv_obj is None:
            serv_obj = self
        self.service('obj_store').add('srv', name, serv_obj)
