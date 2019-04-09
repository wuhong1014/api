#coding:utf-8
import re

import requests
from requests import Request,Response
from utils.dict_format import lower_dict_keys
from utils.exceptions import ParamsError,RequestException,MissingSchema, InvalidSchema, InvalidURL
from utils import log
logger=log.logger()
class ApiResponse(Response):

    def raise_for_status(self):
        if hasattr(self, 'error') and self.error:
            raise self.error
        Response.raise_for_status(self)


class HttpRequest(requests.Session):
    def __init__(self,base_url=None,*arg,**kwargs):
        super(HttpRequest,self).__init__(*arg,**kwargs)
        self.base_url=base_url if base_url else ''
        self.init_case_data()
    def init_case_data(self):
        self.init_data={
            "name": "",
            "data": [
                {
                    "request": {
                        "url": "N/A",
                        "method": "N/A",
                        "headers": {}
                    },
                    "response": {
                        "status_code": "N/A",
                        "headers": {},
                        "encoding": None,
                        "content_type": ""
                    }
                }
            ],
            "data_check": {
                "times": 1,
                'type':'query',
                "sql": "N/A",
                "data_source": {},
            }
        }
    def get_req_resp_record(self,resp_obj):
        """ get request and response info from Response() object.
                """
        def log_print(req_resp_dict,r_type):
            msg="\n-----------{} detail:----------\n".format(r_type)
            for k,v in req_resp_dict[r_type].items():
                msg+="{:<50} : {}".format(k,repr(v))

            logger.debug(msg)
        req_resp_dict={
            "request":{},
            "response":{}
        }
        # record request info
        req_resp_dict['request']['url']=resp_obj.request.url
        req_resp_dict['request']['headers']=dict(resp_obj.request.headers)

        request_body=resp_obj.request.body
        if request_body:
            request_content_type = lower_dict_keys(req_resp_dict['request']['headers']).get('content-type')
            if request_content_type and "multipart/form-data" in request_content_type:
                # upload file type
                req_resp_dict["request"]["body"] = "upload file stream (OMITTED)"
            else:
                req_resp_dict["request"]["body"] = request_body
        log_print(req_resp_dict,'request')

        # record response info
        req_resp_dict["response"]["url"] = resp_obj.url
        req_resp_dict["response"]["status_code"] = resp_obj.status_code
        req_resp_dict["response"]["reason"] = resp_obj.reason
        req_resp_dict["response"]["cookies"] = resp_obj.cookies or {}
        req_resp_dict["response"]["encoding"] = resp_obj.encoding
        resp_headers = dict(resp_obj.headers)
        req_resp_dict["response"]["headers"] = resp_headers

        lower_resp_headers = lower_dict_keys(resp_headers)
        content_type = lower_resp_headers.get("content-type", "")
        req_resp_dict["response"]["content_type"] = content_type

        if "image" in content_type:
            # response is image type, record bytes content only
            req_resp_dict["response"]["content"] = resp_obj.content
        else:
            try:
                # try to record json data
                req_resp_dict["response"]["json"] = resp_obj.json()
            except ValueError:
                # only record at most 512 text charactors
                resp_text = resp_obj.text
                req_resp_dict["response"]["text"] = resp_text[0:512]

        log_print(req_resp_dict, "response")

        return req_resp_dict
    def request(self,method, url, name=None, **kwargs):
        # test name
        self.init_data['name']=name
        # request info
        self.init_data[0]['request']['method']=method
        self.init_data[0]['request']['url']=url
        absolute_http_url_regexp = re.compile(r"^https?://", re.I)
        if absolute_http_url_regexp.match(url):
            pass
        elif self.base_url:
            url="{}/{}".format(self.base_url.rstrip("/"), url.lstrip("/"))
        else:
            logger.error('request :{} --base url missed!'.format(url or name))
            raise ParamsError("base url missed!")
        resp_obj=self._send_request(method,url,**kwargs)
        self.init_data['data']=[self.get_req_resp_record(resp_obj)]
        try:
            resp_obj.raise_for_status()
        except RequestException as e:
            logger.log_error(u"{exception}".format(exception=str(e)))
        else:
            logger.log_info(
                "status_code: {}\n".format(resp_obj.status_code))
        return resp_obj
    def _send_request(self,method, url, **kwargs):
        try:
            msg = "processed request:\n"
            msg += "> {method} {url}\n".format(method=method, url=url)
            msg += "> kwargs: {kwargs}".format(kwargs=kwargs)
            logger.debug(msg)
            return requests.Session.request(self, method, url, **kwargs)
        except requests.RequestException as ex:
            logger.error("RequestException:\n{}".format(str(ex)) )
            raise
