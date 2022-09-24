import os

from eme.entities import load_settings

from tomcru import TomcruCfg, TomcruRouteDescriptor, TomcruEndpointDescriptor, TomcruApiDescriptor, \
    TomcruApiLambdaAuthorizerDescriptor, TomcruLambdaIntegrationDescription, TomcruApiAuthorizerDescriptor


class BaseCfgParser:
    def __init__(self, project, name):
        self.proj = project
        self.name = name
        self.cfg: TomcruCfg = None

    def create_cfg(self, path: str, pck_path):
        self.cfg = TomcruCfg(path, pck_path)

    def parse_project_apis(self):
        """
        Parses api configuration in
        :return:
        """

        path = f'{self.cfg.app_path}/cfg/apis'

        routes = []

        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('routes.ini'):
                    # eme routing file
                    routes.append(os.path.join(path, file))
                elif file.endswith('.ini'):
                    # tomcru api config file
                    self.add_api_cfg(os.path.join(path, file))
                elif file.endswith('.yaml') or file.endswith('.yml'):
                    # swagger file
                    pass

        for routecfg in routes:
            self.add_eme_routes(routecfg, 'http', check_files = True)

    def parse_envvars(self, vendor):
        """
        Parses lambda and other envvars configured
        :return:
        """

        path = f'{self.cfg.app_path}/cfg/{vendor}'

        for env in os.listdir(path):
            envvar_path = os.path.join(path, env, 'envvars')

            if os.path.exists(envvar_path):
                for root, dirs, files in os.walk(envvar_path):
                    for file in files:
                        if file.endswith('.ini'):
                            # envvar file
                            self.add_envvars(os.path.join(envvar_path, file), env, vendor)

    def add_api_cfg(self, file):
        r = load_settings(file, delimiters=('=',)).conf

        authorizers = r.pop('authorizers', {})
        # list authorizers
        for auth_id, integ_opt in authorizers.items():
            auth_integ = self.get_auth_integ(auth_id, integ_opt)

            self.cfg.authorizers[auth_id] = auth_integ

        cfg_all_ = r.pop('__default__', {})

        # list lambdas
        for api_name, cfg in r.items():
            _api_type = cfg.get('type', 'http')
            print(f"Processing api: {api_name}")

            cfg = {**cfg_all_, **cfg}
            #cfg_api_ = self.cfg.apis.setdefault(api_name, TomcruApiDescriptor(api_name, _api_type))
            cfg_api_ = self.cfg.apis[api_name] = TomcruApiDescriptor(api_name, _api_type)

            # map ini to tomcru descriptor
            cfg_api_.swagger_enabled = cfg.get('swagger_enabled', False)
            cfg_api_.swagger_ui = cfg.get('swagger_ui', False)
            cfg_api_.default_authorizer = cfg.get('default_authorizer', None)

    def add_eme_routes(self, file, integration, check_files=False):
        assert integration is not None

        r = load_settings(file, delimiters=('=>', '->')).conf

        # list lambdas
        for api_name, api in r.items():

            _api_type = integration
            if _api_type == 'rest':
                raise Exception("HTTPv1 not supported")

            cfg_api_ = self.cfg.apis.setdefault(api_name, TomcruApiDescriptor(api_name, _api_type))

            print(f"Processing routes: {api_name}")
            for endpoint, integ_opts in api.items():
                if endpoint.startswith('#'):
                    # ignore comments
                    continue

                method, route = endpoint.split(' ')

                endpoint_integ = self.get_integ(api_name, integ_opts, check_files, route, method)

                # add Api Gateway integration
                cfg_api_.routes.setdefault(route, TomcruRouteDescriptor(endpoint_integ.route, endpoint_integ.group, api_name))
                cfg_api_.routes[route].add_endpoint(endpoint_integ)

    def add_openapi_routes(self, api_name, integration=None, check_files=False):
        from openapi_parser import parse

        file = os.path.join(self.cfg.app_path, 'routes', api_name+'.yml')
        if not os.path.exists(file): file = file[:-4] + '.yaml'
        if not os.path.exists(file): raise Exception("File doesnt exist: " + file)
        specification = parse(file)

        for path in specification.paths:
            group = path.url.replace('/', '_').strip('_')
            route = path.url

            for op in path.operations:
                method = op.method.name

                ep = TomcruEndpointDescriptor(group, route, method, lamb, role, layers)
                self.cfg.apis[api_name].setdefault(route, TomcruRouteDescriptor(route, group, api_name))
                self.cfg.apis[api_name][route].add_endpoint(ep)

    def add_layer(self, layer_name, files=None, packages=None, folder=None, single_file=False, in_house=True):
        self.cfg.layers.append((layer_name, files, packages, folder, single_file, in_house))

    def get_integ(self, api_name, integ_opts, check_files: bool, route, method) -> TomcruEndpointDescriptor:
        """

        :param integ_opts:
        :param check_files:
        :param route:
        :param method:
        :return:
        """
        if isinstance(integ_opts, str):
            integ_opts = [integ_opts]
        integ_type, integ_id = integ_opts[0].split(':')

        apicfg = self.cfg.apis[api_name]

        if 'lambda' == integ_type or 'l' == integ_type:
            group, lamb_name = integ_id.split('/')

            auth = self._get_param(integ_opts, 'auth', apicfg.default_authorizer)
            layers = self._get_param(integ_opts, 'layers', apicfg.default_layers)
            role = self._get_param(integ_opts, 'role', apicfg.default_role)

            # post parse layers
            if isinstance(layers, str):
                layers = layers.split("|")
            if len(layers) > 0 and layers[0] == '': layers = layers.pop(0)
            if not auth: auth = None

            # override

            if check_files:
                # check if files exist
                if not os.path.exists(f'{self.cfg.app_path}/lambdas/{group}/{lamb_name}'):
                    print("ERR: Lambda folder", group, integ_id, 'does not exist!')
                    #continue
                    return None

            # Lambda integration
            integ = TomcruLambdaIntegrationDescription(group, route, method, lamb_name, layers, role, auth)
        else:
            raise Exception(f"Integration {integ_type} not recognized!")

        return integ

    def get_auth_integ(self, auth_id, integ_opt) -> TomcruApiAuthorizerDescriptor:
        if not integ_opt:
            return None
        auth_type, integ_opt = integ_opt.split(':')

        if 'lambda' == auth_type or 'l' == auth_type:
            lambda_source, lambda_id = integ_opt.split('/')

            return TomcruApiLambdaAuthorizerDescriptor(auth_id, lambda_id, lambda_source)
        else:
            pass
        raise NotImplementedError(f"auth: {auth_type}")

    def _get_param(self, integ_opts, param, default_val) -> str:
        r = next(filter(lambda x: x.startswith(param+':'), integ_opts), ":").split(':')[1]

        if not r:
            # see if api config contains
            r = default_val

        return r

    def add_envvars(self, file_path, env, vendor):
        """
        Adds enviornment variables ini file defined for:
        - lambda

        :param file_path: ini filepath
        :param env: environment to configure envvars for
        :param vendor: cloud vendor (aws | azure | gpc)
        :return:
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.cfg.app_path, 'cfg', vendor, env, 'envvars', file_path)

        if not os.path.exists(file_path):
            raise Exception(f"Define your envvars in the following directory structure: project/cfg/{vendor}/<env>/envvars/<filename>.ini")

        self.cfg.envs[env] = dict(load_settings(file_path).conf)

    def find_lambda_layers(self):
        raise NotImplementedError("please manually add layers with add_layer")
    #     path = f'{self.cfg.app_path}/layers'
    #
    #     for layer in os.listdir(path):
