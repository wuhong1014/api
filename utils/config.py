import configparser
class Conf:
    '''get config info'''
    def __init__(self,conf_path):
        self.conf_path = conf_path
        self.conf=configparser.ConfigParser()
        self.conf.read(self.conf_path,encoding='utf-8')

    def get_sections(self):
        '''get conf file all sections'name'''
        return self.conf.sections()
    def get_options(self,section):
        '''get all options'name from a section'''
        return  self.conf.options(section)
    def get_values(self,section,options):
        ''' if options is str ,get a option's value  from a section
            if options is list,get all option's values from  a section
        '''
        dictres = {}
        if isinstance(options, list):
            for op in options:
                dictres[op] = self.conf.get(section, op)
        else:
            dictres[options] = self.conf.get(section, options)
        return dictres
    def get_value(self,section,option):
        return self.conf.get(section,option)