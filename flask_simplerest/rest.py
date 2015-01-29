# -*- coding: utf-8 -*-
"""
    smartwall.base
    ~~~~~~~~~~~~~~

    This module contains building blocks for the REST api such as:

    * Error classes
    * Base class for views
    * Decorators

    :author: Felipe Blassioli <felipe.blassioli@vtxbrasil.com.br>
"""
from functools import wraps
from flask import request, abort, jsonify, Response, current_app
from flask.ext.classy import FlaskView

from .error import ApiError, RowDoesNotExist, DuplicateKeyError

def wrap_response(f):
    """Decorator that jsonifies view responses
    and also catches relevant errors.
    """
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        try:
            resp = f(*args, **kwargs)
        except Exception as error:
            if current_app.config.get('RAISE_EXCEPTIONS', True):
                raise error
            else:
                class_name = error.__class__.__name__
                if class_name.find("DoesNotExist") != -1:
                    resp = RowDoesNotExist(error)
                elif class_name.find("IntegrityError") != -1:
                    resp = DuplicateKeyError(error)
                else:
                    resp = error
        if isinstance(resp, Response):
            return resp
        elif isinstance(resp, list):
            return jsonify({'data': resp})
        elif hasattr(resp,'to_json'):
            return jsonify(resp.to_json())
        else:
            return jsonify(resp)
    return wrapped_f

class RestView(FlaskView):
    """The RestView class that logs requests and responses
    and parses params from the request object according to self.rules variable.
    """
    decorators = [wrap_response]

    def __init__(self):
        self.parsers = {}
        if hasattr(self, "args_rules"):
            for name in self.args_rules:
                self.parsers[name] = ArgsParser(self.args_rules[name])
        else:
            self.args_rules = {}

    def before_request(self, name, *args, **kwargs):
        if name in self.parsers:
            self.args = self.parsers[name].parse(request)
        else:
            current_app.logger.warning("Parser not found! name=[%s]" % name)
            self.args = {}
        
    def after_request(self, name, response):
        req = request.method + ' ' + request.url
        if response.mimetype == 'text/html':
            current_app.logger.debug("{:<45} response: text/html".format(req))
        else:
            resp = str(response.data)
            fmt = "{:<45} response: {}"
            if 'LOG_MAX_RESP_SIZE' in current_app.config:
                end = current_app.config['LOG_MAX_RESP_SIZE']
                msg = fmt.format(req,resp[:end]) + 'length=[{}]'.format(len(resp))
            else:
                msg = fmt.format(req,resp)
            current_app.logger.debug(msg)
        return response

from json import loads
class Argument(object):

    def __init__(self, name, default=None, required=True, type=None, description=None, case_sensitive=True, coerce=loads):
        self.name = name
        self.default = default
        self.required = required
        self.type = type
        self.description = description
        self.case_sensitive = case_sensitive
        self.coerce = coerce

    def __repr__(self):
        return "Arg({},default={})".format(self.name,self.default)

class ArgsParser(object):

    def __init__(self, args=None):
        self.args = args or []

    def add_argument(self, *args, **kwargs):
        self.args.current_append(Argument(*args, **kwargs))

    def add_arguments(self, params):
        self.args.extend(params)

    def parse(self, request):
        """
        Parses the request parameters according to rules(self.args).
        """
        result = {}
        if request.method.lower() == 'post':
            params = request.get_json(
                cache=False) if request.mimetype == 'application/json' else request.form
        else:
            params = request.args
        for arg in self.args:
            if arg.name in params:
                if arg.type is not None and type(params[arg.name]) != arg.type:
                    try:
                        result[arg.name] = arg.coerce(params[arg.name])
                    except Exception as err:
                        current_app.logger.warning('Coercion failed for param: {}'.format(arg.name))
                        abort(400)
                else:
                    result[arg.name] = params[arg.name]
            elif arg.required:
                current_app.logger.warning("Missing required param: {}".format(arg.name))
                abort(400)
            else:
                result[arg.name] = arg.default
        return result

from flask import url_for, jsonify, make_response, render_template
class InfoView(RestView):
    def map(self):
        links = []
        for rule in current_app.url_map.iter_rules():
            s = '{} {} -> {}'.format(list(rule.methods), str(rule), rule.endpoint)
            links.append(s)
        return links

    def log(self):
        with open(current_app.config['LOG_FILENAME']) as f:
            lines = f.readlines()
            params = dict(
                line_count = len(lines),
                log_content = ''.join(lines)
            )
            return make_response(render_template('view_log.html', **params))
        return dict(result="error")

    def config(self):
        resp = dict()
        for k,v in current_app.config.items():
            try:
                dumps(v)
                resp[k] = v
            except Exception, err:
                resp[k] = str(v)
        return resp


from flask.json import JSONEncoder
import calendar
from datetime import datetime
from decimal import Decimal
class DefaultJSONEncoder(JSONEncoder):

    def default(self, obj, *args, **kwargs):
        if hasattr(obj,'to_json'):
            return obj.to_json()
        try:
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                if obj.utcoffset() is not None:
                    obj = obj - obj.utcoffset()
                millis = int(
                    calendar.timegm(obj.timetuple()) * 1000 +
                    obj.microsecond / 1000
                )
                return millis
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

def default_error_handler(error):
    if current_app.config.get('RAISE_EXCEPTIONS', True):
        raise error
    # This sucks: the jsonify dumpings won`t allow to_json() to return dict(error)
    resp = jsonify(dict(error=error))
    if hasattr(error, 'status_code'):
        resp.status_code = error.status_code
    else:
        resp.status_code = 400
    current_app.logger.error(repr(error) + "msg=" + str(error))
    return resp

class RestAPI(object):
    def __init__(self, app, json_encoder=DefaultJSONEncoder, error_handler=default_error_handler):
        self.app = app
        self.app.view_classes = {}
        self.json_encoder = json_encoder
        self.error_handler = error_handler

        self.app.json_encoder = self.json_encoder
        self.app.register_error_handler(Exception, default_error_handler)

        InfoView.register(self.app)

    def register(self, view):
        self.app.view_classes[view.__name__] = view
        view.register(self.app)

    def register_all(self, *args):
        for v in args:
            self.register(v)

