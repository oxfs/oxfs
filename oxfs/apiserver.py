#!/usr/bin/env python

import os, json
import threading
from flask import Flask, request
from flask_restplus import Resource, Api, fields
from werkzeug.middleware.proxy_fix import ProxyFix

class OxfsApi(object):
    def __init__(self, oxfs_fuse):
        self.oxfs_fuse = oxfs_fuse

    def reload_path(self, path):
        self.oxfs_fuse.attributes.remove(path)
        entries = self.oxfs_fuse.directories.fetch(path)
        if entries:
            self.oxfs_fuse.directories.remove(path)
            for item in entries:
                self.oxfs_fuse.attributes.remove(os.path.join(path, item))
        return True

    def dump_directories(self, path):
        return True, json.dumps(self.oxfs_fuse.directories.fetch(path))

    def run(self):
        self.thread = threading.Thread(target=self.start_service)
        self.thread.daemon = True
        self.thread.start()

    def start_service(self):
        apiserver = self
        self.app = Flask(__name__)
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app)
        self.api = Api(self.app, version='1.0', title='Oxfs Api',
                       description='The Oxfs Api')

        # Response model
        fs_namespace = self.api.namespace('fs', description='fs operations')
        status_model = self.api.model(
            'Status',
            {
                'status': fields.Boolean,
                'data': fields.String
            })

        # Request arguments
        string_args = self.api.parser()
        string_args.add_argument('path', required=True, help='absolute path')

        # Api
        @fs_namespace.route('/reload')
        @fs_namespace.expect(string_args)
        class Reload(Resource):
            @fs_namespace.marshal_with(status_model, envelope='data')
            def post(self):
                args = string_args.parse_args()
                path = apiserver.oxfs_fuse.remotepath(args['path'])
                status = apiserver.reload_path(path)
                return {'status': status, 'data': path}

        @fs_namespace.route('/directories')
        @fs_namespace.expect(string_args)
        class Directories(Resource):
            @fs_namespace.marshal_with(status_model, envelope='data')
            def get(self):
                args = string_args.parse_args()
                path = apiserver.oxfs_fuse.remotepath(args['path'])
                status, data = apiserver.dump_directories(path)
                return {'status': status, 'data': data}

        self.app.run(port=10010)
