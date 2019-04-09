# encoding: utf-8

import json
import re

from utils import exceptions, log,query_json,dict_format
from collections import OrderedDict
from requests.models import PreparedRequest
from requests.structures import CaseInsensitiveDict
logger=log.logger()
text_extractor_regexp_compile = re.compile(r".*\(.*\).*")


class ResponseObject(object):

    def __init__(self, resp_obj):
        """ initialize with a requests.Response object

        Args:
            resp_obj (instance): requests.Response instance

        """
        self.resp_obj = resp_obj

    def __getattr__(self, key):
        try:
            if key == "json":
                value = self.resp_obj.json()
            elif key == "cookies":
                value =  self.resp_obj.cookies.get_dict()
            else:
                value =  getattr(self.resp_obj, key)

            self.__dict__[key] = value
            return value
        except AttributeError:
            err_msg = "ResponseObject does not have attribute: {}".format(key)
            logger.log_error(err_msg)
            raise exceptions.ParamsError(err_msg)

    def _extract_field_with_regex(self, field):
        """ extract field from response content with regex.
            requests.Response body could be json or html text.

        Args:
            field (str): regex string that matched r".*\(.*\).*"

        Returns:
            str: matched content.

        Raises:
            exceptions.ExtractFailure: If no content matched with regex.

        Examples:
            >>> # self.text: "LB123abcRB789"
            >>> filed = "LB[\d]*(.*)RB[\d]*"
            >>> _extract_field_with_regex(field)
            abc

        """
        matched = re.search(field, self.text)
        if not matched:
            err_msg = u"Failed to extract data with regex! => {}\n".format(field)
            err_msg += u"response body: {}\n".format(self.text)
            logger.log_error(err_msg)
            raise exceptions.ExtractFailure(err_msg)

        return matched.group(1)

    def _extract_field_with_delimiter(self, field):
        """ response content could be json or html text.

        Args:
            field (str): string joined by delimiter.
            e.g.
                "status_code"
                "headers"
                "cookies"
                "content"
                "headers.content-type"
                "content.person.name.first_name"

        """
        # string.split(sep=None, maxsplit=-1) -> list of strings
        # e.g. "content.person.name" => ["content", "person.name"]
        try:
            top_query, sub_query = field.split('.', 1)
        except ValueError:
            top_query = field
            sub_query = None

        # status_code
        if top_query in ["status_code", "encoding",  "reason", "url"]:
            if sub_query:
                # status_code.XX
                err_msg = u"Failed to extract: {}\n".format(field)
                logger.log_error(err_msg)
                raise exceptions.ParamsError(err_msg)

            return getattr(self, top_query)

        # cookies
        elif top_query == "cookies":
            cookies = self.cookies
            if not sub_query:
                # extract cookies
                return cookies

            try:
                return cookies[sub_query]
            except KeyError:
                err_msg = u"Failed to extract cookie! => {}\n".format(field)
                err_msg += u"response cookies: {}\n".format(cookies)
                logger.log_error(err_msg)
                raise exceptions.ExtractFailure(err_msg)



        # headers
        elif top_query == "headers":
            headers = self.headers
            if not sub_query:
                # extract headers
                return headers

            try:
                return headers[sub_query]
            except KeyError:
                err_msg = u"Failed to extract header! => {}\n".format(field)
                err_msg += u"response headers: {}\n".format(headers)
                logger.log_error(err_msg)
                raise exceptions.ExtractFailure(err_msg)

        # response body
        elif top_query in ["content", "text", "json"]:
            try:
                body = self.json
            except exceptions.JSONDecodeError:
                body = self.text

            if not sub_query:
                # extract response body
                return body

            if isinstance(body, (dict, list)):
                # content = {"xxx": 123}, content.xxx
                return query_json.query_json(body, sub_query)
            elif sub_query.isdigit():
                # content = "abcdefg", content.3 => d
                return query_json.query_json(body, sub_query)
            else:
                # content = "<html>abcdefg</html>", content.xxx
                err_msg = u"Failed to extract attribute from response body! => {}\n".format(field)
                err_msg += u"response body: {}\n".format(body)
                logger.log_error(err_msg)
                raise exceptions.ExtractFailure(err_msg)


        else:
            err_msg = u"Failed to extract attribute from response! => {}\n".format(field)
            err_msg += u"available response attributes: status_code, cookies,  headers, content, text, json, encoding,  reason, url.\n\n"
            err_msg += u"response.new_attribute = 'new_attribute_value'\n"
            logger.log_error(err_msg)
            raise exceptions.ParamsError(err_msg)

    def extract_field(self, field):
        """ extract value from requests.Response.
        """
        if not isinstance(field, str):
            err_msg = u"Invalid extractor! => {}\n".format(field)
            logger.log_error(err_msg)
            raise exceptions.ParamsError(err_msg)

        msg = "extract: {}".format(field)

        if text_extractor_regexp_compile.match(field):
            value = self._extract_field_with_regex(field)
        else:
            value = self._extract_field_with_delimiter(field)



        msg += "\t=> {}".format(value)
        logger.log_debug(msg)

        return value

    def extract_response(self, extractors):
        """ extract value from requests.Response and store in OrderedDict.

        Args:
            extractors (list):

                [
                    {"resp_status_code": "status_code"},
                    {"resp_headers_content_type": "headers.content-type"},
                    {"resp_content": "content"},
                    {"resp_content_person_first_name": "content.person.name.first_name"}
                ]

        Returns:
            OrderDict: variable binds ordered dict

        """
        if not extractors:
            return {}

        logger.log_debug("start to extract from response object.")
        extracted_variables_mapping = OrderedDict()
        extract_binds_order_dict = dict_format.ensure_mapping_format(extractors)

        for key, field in extract_binds_order_dict.items():
            extracted_variables_mapping[key] = self.extract_field(field)

        return extracted_variables_mapping
