from json import dumps, loads
# from urllib.request import Request, urlopen, HTTPError
from urllib2 import Request, urlopen, HTTPError


class JsonClient:

    def __init__(self, endpoint, hsl2_helper, headers=None):
        self.endpoint = endpoint
        self.help = hsl2_helper
        if type(headers) is dict:
            self.headers = headers
        else:
            self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json; charset=utf-8'}
        self.token_header = None

    def inject_auth_token(self, token, headername='Authorization'):
        if token:
            self.token_header = {headername: token}
        else:
            self.token_header = None
        return self

    def execute(self, body=None, additional_headers=None, charset='utf-8'):
        headers = dict(self.headers)
        if self.token_header:
            headers.update(self.token_header)
        if type(additional_headers) is dict:
            headers.update(additional_headers)

        if body:  # With body == POST
            req = Request(self.endpoint, data=dumps(body), headers=headers)
        else:
            req = Request(self.endpoint, headers=headers)

        try:
            return loads(urlopen(req).read().decode(charset))
        except HTTPError:
            if self.help:
                self.help.log_err("HTTPError in Json Client: URL: " + self.endpoint + "; Body: " + str(body) +
                                  "; Headers: " + str(headers))
