class Error(Exception):
    """ Base class for Errors """
    pass

class ApiError(Error):

    """
    An error that will be jsonified and sent to the client (hopefully)
    """

    status_code = 400

    def __init__(self, emsg, etype="GenericException", ecode=666, details=None):
        self.message = emsg
        self.type = etype
        self.code = ecode
        if details != None:
            self.details = details

    def to_json(self):
        _data = self.__dict__
        _data.pop('status_code', None)
        return _data

    @staticmethod
    def from_exception(err):
        return ApiError(str(err))

    def __str__(self):
        return self.message

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