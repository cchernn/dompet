import cgi
import io
import json

class Params:
    def __init__(self, event):
        self.user = self.getUserID(event)
        self.http_method = self.getHTTPMethod(event)
        self.path = self.getPath(event)
        self.headers = self.getHeaders(event)
        self.body = self.getBody(event)
        self.pathParams = self.getPathParams(event)
    
    @classmethod
    def getUserID(cls, event):
        return event.get("requestContext").get("authorizer").get("claims").get("sub")
    
    @classmethod
    def getHTTPMethod(cls, event):
        return event.get('httpMethod')
    
    @classmethod
    def getPath(cls, event):
        return event.get('path')
    
    @classmethod
    def getPathParams(cls, event):
        return event.get('pathParameters')
    
    @classmethod
    def getHeaders(cls, event):
        headers = event.get("headers")
        headers = {k.lower(): v for k, v in headers.items()}
        return headers

    @classmethod
    def getBody(cls, event):
        headers = cls.getHeaders(event)
        if event.get('body', None) not in [None, "None"]:
            content_type = headers.get("content-type")
            if "multipart/form-data" in content_type:
                fp = io.BytesIO(event.get("body").encode("utf-8"))
                pdict = cgi.parse_header(content_type)[1]
                if "boundary" in pdict:
                    pdict["boundary"] = pdict["boundary"].encode("utf-8")
                pdict["CONTENT-LENGTH"] = len(event.get("body"))
                body = cgi.parse_multipart(fp, pdict)
                for key, value in body.items():
                    if isinstance(value, list):
                        body[key] = value[0]
                return body
            elif "application/json" in content_type:
                return json.loads(event.get('body'))
            return event.get('body')
        return None