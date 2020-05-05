from http.server import BaseHTTPRequestHandler
from common_part import proxy_common_move, CLIENT_LIST
import requests


########################################################################################################################
# ------------------------------------------- server via http lib ------------------------------------------------------
########################################################################################################################
class HttpProxyImgCompressor(BaseHTTPRequestHandler):
    def do_GET(self):
        response_content = proxy_common_move(req_handler=self, get_method=requests.get)

        if response_content is not None:
            self.wfile.write(response_content)
        else:
            print('bad response content')
            self._send_bad_client_response()
            print("-------------------------------------")

    def do_CONNECT(self):
        if self.client_address[0] in CLIENT_LIST:
            self.send_response(200)
            print('localhost connected')

    def _send_bad_client_response(self):
        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<h1>Sorry bro<h1>")
