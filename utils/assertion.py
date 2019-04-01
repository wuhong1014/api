#coding:utf-8

class BaseFailure(Exception):
    pass

class FileNotFound(BaseFailure):
    pass