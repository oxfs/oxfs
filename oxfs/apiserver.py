#!/usr/bin/env python

import threading
import os, json, shutil
from flask import Flask, request
from flask_restx import Resource, Api, fields
from werkzeug.middleware.proxy_fix import ProxyFix

class OxfsApi(object):
    def __init__(self, oxfs_fuse):
        self.oxfs_fuse = oxfs_fuse

    def cleanf(self, path):
        '''clear the file attributes cache, file cache.'''
        self.oxfs_fuse.attributes.remove(path)
        cachefile = self.oxfs_fuse.cachefile(path)
        if os.path.exists(cachefile):
            os.unlink(cachefile)
        return True

    def cleand(self, path):
        '''clear the directories cache, 1st level file cache.'''
        entries = self.oxfs_fuse.directories.fetch(path)
        if entries:
            self.oxfs_fuse.directories.remove(path)
            for name in entries:
                self.cleanf(os.path.join(path, name))
        return True

    def clear(self):
        '''clear all attributes, directories cache.'''
        self.oxfs_fuse.attributes.cache.clear()
        self.oxfs_fuse.directories.cache.clear()
        shutil.rmtree(self.oxfs_fuse.cache_path)
        os.makedirs(self.oxfs_fuse.cache_path)
        return True

    def fetchd(self, path):
        return True, json.dumps(self.oxfs_fuse.directories.fetch(path))

    def run(self, port):
        self.thread = threading.Thread(target=self.start_service, args=(port,))
        self.thread.daemon = True
        self.thread.name = 'apiserver'
        self.thread.start()

    def set_flask_env(self):
        name = 'FLASK_ENV'
        if name not in os.environ:
            os.environ[name] = 'development'

    def start_service(self, port):
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
                status = (apiserver.cleanf(path), apiserver.cleand(path))
                return {'status': False not in status, 'data': path}

        @fs_namespace.route('/clear')
        class Clear(Resource):
            @fs_namespace.marshal_with(status_model, envelope='data')
            def delete(self):
                status = apiserver.clear()
                return {'status': True, 'data': 'success'}

        @fs_namespace.route('/directories')
        @fs_namespace.expect(string_args)
        class Directories(Resource):
            @fs_namespace.marshal_with(status_model, envelope='data')
            def get(self):
                args = string_args.parse_args()
                path = apiserver.oxfs_fuse.remotepath(args['path'])
                status, data = apiserver.fetchd(path)
                return {'status': status, 'data': data}

        self.set_flask_env()
        self.app.run(port=port, debug=False)
