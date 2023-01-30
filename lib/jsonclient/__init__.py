import ssl
from urllib2 import Request, urlopen, HTTPError
import json


class JsonClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.token = None
        self.headername = None

    def inject_token(self, token, headername='Authorization'):
        self.token = token
        self.headername = headername

    def execute(self, query, variables=None):
        data = {'query': query,
                'variables': variables}
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        if self.token is not None:
            headers[self.headername] = str(self.token)

        req = Request(self.endpoint, data=json.dumps(data), headers=headers)

        try:
            ctx = ssl._create_unverified_context()
            response = urlopen(req, context=ctx)
            return response.read().decode('utf-8')
        except HTTPError as e:
            print(e.read())
            raise e
