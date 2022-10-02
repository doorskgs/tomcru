from tomcru import TomcruProject

from .flask_runner import start_flask_app


class EmeAppBuilder:
    def __init__(self, project: TomcruProject, env, **kwargs):
        self.p = project
        self.cfg = project.cfg
        self.env = env
        self.apis = []
        #self.opts =

        # todo: add to configuration?
        self.api2builder = {
            'http': 'aws:onpremise:aggr_api',
            'ws': 'aws:onpremise:aggr_ws',
            'mocked_api': 'aws:onpremise:mocked_api',
        }

    def build_app(self, env):
        self.env = env

        for api_name, api in self.cfg.apis.items():

            if not api.enabled:
                continue

            api.api_name = api_name
            app = self.p.serv(self.api2builder[api.api_type]).build_api(api_name, api, env)
            self.apis.append(app)

        return self.apis

    def run_apps(self, apps, env, main_api=None, filter_apps=None):
        if main_api is None:
            main_api = next(iter(apps)).api_name

        apps.sort(key=lambda x: x.api_name == main_api)

        for app in apps:
            if not filter_apps or app.api_name in filter_apps:
                start_flask_app(app.api_name, app, env=env, threaded=not app.api_name == main_api)
