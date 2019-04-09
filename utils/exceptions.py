# coding:utf-8


'''   Failure type Exception  '''


class BaseFailure(Exception):
    pass


class ExtractFailure(BaseFailure):
    pass


'''error type Exception'''

'''   Error type Exception  '''
class BaseError(Exception):
    pass


class FileFormatError(BaseError):
    pass


class FuncFormatError(BaseError):
    pass


class FunctionNotFound(BaseError):
    pass


class VariableNotFound(BaseError):
    pass


class ParamsError(BaseError):
    pass


class JSONDecodeError(BaseError):
    pass

