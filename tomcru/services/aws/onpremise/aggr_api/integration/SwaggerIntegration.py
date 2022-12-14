import json
import os
from functools import cache
from io import StringIO
from json import JSONEncoder

#import yaml
from tomcru.yaml_custom import yaml

from flask import request, Response, Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from tomcru import TomcruApiDescriptor, TomcruSwaggerIntegrationDescription

from .TomcruApiGWHttpIntegration import TomcruApiGWHttpIntegration


#
# class TomcruSpecialObjectsJSONEncoder(JSONEncoder):
#     def default(self, obj):
#         if hasattr(obj, '_tomcru_json_serializer'):
#             return str(obj._tomcru_json_serializer)
#
#         return JSONEncoder.default(self, obj)
#


class SwaggerIntegration(TomcruApiGWHttpIntegration):

    def __init__(self, api: TomcruApiDescriptor, endpoint: TomcruSwaggerIntegrationDescription, swagger_converter, env=None):
        # self.spec = api.spec
        # self.api_name = api.api_name
        self.api = api
        self.endpoint = endpoint
        self.env = env
        self.swagger_converter = swagger_converter

    def on_request(self, **kwargs):

        # todo: we don't really need auth here, but maybe?

        if self.endpoint.type == 'ui':
            # display swagger UI
            return "Something went wrong with the onpremise request transition of Swagger UI."
        elif self.endpoint.type == 'spec':
            swagger_content = self.get_swagger_content(self.api, self.endpoint)

            r = Response(swagger_content, status=200)
            r.headers['content-type'] = self.content_type
            return r

    @cache
    def get_swagger_content(self, api: TomcruApiDescriptor, endpoint):
        self.content_type = f'application/{endpoint.req_content}'

        if not api.spec:
            # generate swagger from tomcru cfg
            api.spec = self.swagger_converter.convert_to_swagger(api)

        if 'json' == endpoint.req_content:
            swagger_content = json.dumps(api.spec)
        else:
            sth = StringIO()
            yaml.dump(api.spec, stream=sth)
            swagger_content = sth.getvalue()

        return swagger_content

def integrate_swagger_ui_blueprint(app: Flask, swagger_endpoint: TomcruSwaggerIntegrationDescription, ui_endpoint: TomcruSwaggerIntegrationDescription):
    swaggerui_blueprint = get_swaggerui_blueprint(
        ui_endpoint.route,
        swagger_endpoint.route,
        config={
            # Swagger UI config overrides
            #'app_name':
        },
        # oauth_config={  # OAuth config. See https://github.com/swagger-api/swagger-ui#oauth2-configuration .
        #    'clientId': "your-client-id",
        #    'clientSecret': "your-client-secret-if-required",
        #    'realm': "your-realms",
        #    'appName': "your-app-name",
        #    'scopeSeparator': " ",
        #    'additionalQueryStringParams': {'test': "hello"}
        # }
    )

    app.register_blueprint(swaggerui_blueprint)
