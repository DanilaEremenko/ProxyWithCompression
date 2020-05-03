import inspect
import socket
import requests
from io import BytesIO
from PIL import Image
from http.server import BaseHTTPRequestHandler

########################################################################################
# ---------------------------------- server params -------------------------------------
########################################################################################
CLIENT_LIST = ('127.0.0.1', '192.168.1.70')
MAX_IMG_SIZE = (64, 64)


def whoami():
    return inspect.stack()[1][3]


########################################################################################
# ---------------------------------- via socket lib ------------------------------------
########################################################################################
class SimpleHttpServer():
    def __init__(self, TCP_IP='', TCP_PORT=8080, BUFFER_SIZE=1024):
        self.BUFFER_SIZE = BUFFER_SIZE  # Normally 1024, but we want fast response
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((TCP_IP, TCP_PORT))
        self.s.listen(1)

    ###############################################################################
    # ----------------------- parsing stuff --------------------------------------
    ###############################################################################
    def http_req_to_str(self):
        res = "%s %s %s\r\n" % (self.type, self.path, self.http_v)
        for key, value in self.headers.items():
            res += "%s: %s\r\n" % (key, value)
        res += '\r\n'
        return res

    def parst_http(self, input_str, verbose=False):
        lines = input_str.split('\r\n')
        self.verbose_print(function=whoami(), message='parsing http body')
        if verbose:
            print("-------------------------------")
            for line in lines:
                print(line)
            print("-------------------------------")

        self.path = lines[0]
        self.type = lines[0].split(' ')[0]
        self.path = lines[0].split(' ')[1]
        self.http_v = lines[0].split(' ')[2]

        self.headers = {}
        for line in lines[1:]:
            if line != '':
                line_args = line.split(': ')
                self.headers[line_args[0]] = line_args[1]

        if self.http_req_to_str() != input_str:
            raise Exception('can not to reapir input str from parsed req')
        else:
            self.verbose_print(function=whoami(), message='body repaired from fields, test passed')

    ###############################################################################
    # ----------------------- socket stuff --------------------------------------
    ###############################################################################
    def recv_text(self, sock):
        r'''Receive everything from `sock`, until timeout occurs, meaning sender
        is exhausted, return result as string.'''

        # dirty hack to simplify this stuff - you should really use zero timeout,
        # deal with async socket and implement finite automata to handle incoming data

        prev_timeout = sock.gettimeout()
        try:
            sock.settimeout(0.01)

            rdata = []

            # ---------------------------------- read headers ----------------------------------
            while True:
                try:
                    self.verbose_print(function=whoami(), message='reading text chunk')
                    rdata.append(sock.recv(self.BUFFER_SIZE).decode())
                    self.verbose_print(function=whoami(), message='text chunk readed')
                    if rdata[0][-4:] == '\r\n\r\n':
                        self.verbose_print(function=whoami(), message='all text readed, next go to the data reading')
                        return ''.join(rdata)
                except socket.timeout:
                    if len(rdata) == 0:
                        self.verbose_print(function=whoami(), message='empty rdata array got')
                        return None
                    else:
                        self.verbose_print(function=whoami(), message='rdata returned')
                        return ''.join(rdata)

            # unreachable
        finally:
            sock.settimeout(prev_timeout)

    def recv_data(self, sock):
        # prev_timeout = sock.gettimeout()
        data = b''
        try:
            self.verbose_print(function=whoami(), message='setting timeout')
            sock.settimeout(0.01)
            self.verbose_print(function=whoami(), message='timeout seted')
            # ---------------------------------- read headers ----------------------------------
            while True:
                try:
                    self.verbose_print(function=whoami(), message='reading data chunk')
                    new_data = sock.recv(self.BUFFER_SIZE)
                    self.verbose_print(function=whoami(), message='data chunk readed')
                    data += new_data
                    self.verbose_print(function=whoami(), message='data chunks joined')

                except socket.timeout:
                    self.verbose_print(function=whoami(), message='data returned')
                    return data

            # unreachable
        finally:
            self.verbose_print(function=whoami(), message='timeout on socket while data parsing?')
            return data

    ###############################################################################
    # ----------------------- versbosity ------------------------------------------
    ###############################################################################
    def verbose_print(self, function, message):
        print("--%s: %s" % (function.upper(), message))

    ###############################################################################
    # ----------------------- api emulating part -----------------------------------
    ###############################################################################
    def send_response(self, code):
        self.conn.send(('%s %d %s' % ('HTTP/1.1', code, 'OK')).encode())

    def send_header(self, keyword, value):
        self.conn.send('%s: %s\n'.encode() % (keyword, value))

    def end_headers(self):
        self.conn.send('\r\n\r\n'.encode())

    def process_request(self):
        if self.type == 'GET':
            print('GET: getting response content from request processing function')
            response_content = proxy_common_move(self)
            print('GET: response content getted')
            try:
                self.conn.send(response_content)
                print('GET: response content resended')
            except:
                print('GET: can not send response content')

            print('GET: proceesed, exiting...')
            # if self.headers['Proxy-Connection'] == 'keep-alive':
            #     print('GET: connection keeped')
            # else:
            #     self.conn.close()
            #     print('GET: connection closed')
            self.conn.close()
            print('GET: connection closed')
            print('________________________________________________\n\n\n')

        elif self.type == 'CONNECT':
            self.send_response(200)
            print('CONNECT processed, keeping connection...')
            print('________________________________________________\n\n\n')
            self.end_headers()
            self.conn.send(self.data)

        else:
            raise Exception('Undefined method %s' % self.type)

    ###############################################################################
    # ----------------------- MAIN STUFF --------------------------------------
    ###############################################################################
    def serve_forever(self):

        parse_only_data = False
        while True:
            self.conn, (self.client_address, self.client_port) = self.s.accept()
            print('\n\n\n_________________________________________________________')
            self.verbose_print(function=whoami(),
                               message='new connection %s: %s' % (self.client_address, self.client_port))

            is_okay = True
            while is_okay:
                # if not parse_only_data:
                self.rdata = self.recv_text(self.conn)
                self.data = self.recv_data(self.conn)

                # parse_only_data = True if self.data == b'' else False

                if not self.rdata:
                    is_okay = False
                    self.verbose_print(function=whoami(), message='rdata is not, exiting...')
                else:
                    self.parst_http(input_str=self.rdata, verbose=True)
                    self.process_request()
                    is_okay = False


########################################################################################
# ---------------------------------- server via http lib -------------------------------
########################################################################################
class HttpProxyImgCompressor(BaseHTTPRequestHandler):
    def do_GET(self):
        response_content = proxy_common_move(self)

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


##########################################################################
# ------------------------ COMMON ----------------------------------------
##########################################################################
def proxy_common_move(req_handler):
    def image_to_byte_array(image):
        imgByteArr = BytesIO()
        image.save(imgByteArr, format=image.format)
        imgByteArr = imgByteArr.getvalue()
        return imgByteArr

    if req_handler.client_address[0] in CLIENT_LIST:
        req_res = req_handler.path
        print('requested resource %s' % req_res)
        resp = requests.get(req_res)

        changed_resp_content = resp.content

        req_handler.send_response(resp.status_code)

        for keyword, value in dict(resp.headers).items():
            # print("%s:%s" % (keyword, value))
            if keyword.lower() == 'content-type':

                print('content-type:%s' % value)
                req_handler.send_header(keyword, value)

                if value.lower() == 'image/png':
                    img = Image.open(BytesIO(resp.content))
                    if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                        print("img compressed")
                        img.thumbnail(MAX_IMG_SIZE)
                        changed_resp_content = image_to_byte_array(img)
        req_handler.end_headers()
        return changed_resp_content

    else:
        return None
