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

class Error(Exception):
    """ Base class for Errors """
    pass


class ApiError(Error):

    """
    An error that will be jsonified and sent to the client (hopefully)
    """

    def __init__(self, emsg, etype="GenericException", ecode=666, details=None):
        self.message = emsg
        self.type = etype
        self.code = ecode
        if details != None:
            self.details = details

    @staticmethod
    def from_exception(err):
        return ApiError(str(err))


class RowDoesNotExist(ApiError):

    def _parse(self, exception):
        name = exception.__class__.__name__
        details = str(exception)
        schema = name[:name.find("DoesNotExist")]
        row_id = details[details.find('PARAMS: ['):][9]
        msg = "Row not found for id = [{}]. Schema = [{}].".format(
            row_id, schema)
        return msg, details

    def __init__(self, exception):
        msg, details = self._parse(exception)
        ApiError.__init__(self, msg, "DatabaseException", 110, details=details)


class DuplicateKeyError(ApiError):

    def _parse(self, exception):
        details = str(exception)
        msg = exception.args[1]
        # msg[msg.find('Duplicate'):-2]
        return msg, details

    def __init__(self, exception):
        msg, details = self._parse(exception)
        ApiError.__init__(self, msg, "DatabaseException", 120, details=details)

def wrap_response(f):
    """Decorator that jsonifies view responses
    and also catches relevant errors.
    """
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        try:
            resp = f(*args, **kwargs)
        except ApiError, err:
            resp = {'error': err.__dict__}
        except Exception, err:
            if current_app.config.pop('RAISE_EXCEPTIONS', True):
                raise err
            else:
                class_name = err.__class__.__name__
                if class_name.find("DoesNotExist") != -1:
                    resp = {'error': RowDoesNotExist(err).__dict__}
                elif class_name.find("IntegrityError") != -1:
                    resp = {'error': DuplicateKeyError(err).__dict__}
                else:
                    current_app.logger.error(repr(err) + "msg=" + str(err))
                    resp = {'error': ApiError.from_exception(err).__dict__}
        if isinstance(resp, Response):
            return resp
        elif isinstance(resp, list):
            return jsonify({'data': resp})
        elif isinstance(resp, ApiError):
            return jsonify({'error': resp.__dict__})
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


class Argument(object):

    def __init__(self, name, default=None, required=True, type=unicode, description=None, case_sensitive=True):
        self.name = name
        self.default = default
        self.required = required
        self.type = type
        self.description = description
        self.case_sensitive = case_sensitive

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


#if not current_app.config.pop('USE_DEFAULT_JSON_ENCODER', False):
from flask.json import JSONEncoder
import calendar
from datetime import datetime
class CustomJSONEncoder(JSONEncoder):

    def default(self, obj, *args, **kwargs):
        if hasattr(obj,'to_json'):
            return obj.to_json()
        try:
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

class RestAPI(object):
    def __init__(self, app, use_custom_json_encoder=True):
        self.app = app
        if use_custom_json_encoder:
            self.app.json_encoder = CustomJSONEncoder

    def register(self, views):
        self.app.view_classes = {}
        for v in views:
            self.app.view_classes[v.__name__] = v
        for v in self.app.view_classes.values():
            v.register(self.app)

        InfoView.register(self.app)
        print self.app.view_classes