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


########################################################################################
# ---------------------------------- via socket lib ------------------------------------
########################################################################################
class SimpleHttpServer():
    def __init__(self, TCP_IP='', TCP_PORT=8080):
        self.BUFFER_SIZE = 1024  # Normally 1024, but we want fast response
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((TCP_IP, TCP_PORT))
        self.s.listen(1)

    ###############################################################################
    # ----------------------- parsing stuff --------------------------------------
    ###############################################################################
    def http_req_to_str(self):
        res = "%s %s %s\r\n" % (self.type, self.path, self.http_v)
        for header in self.headers:
            res += "%s: %s\r\n" % (header['key'], header['value'])
        res += '\r\n'
        return res

    def parst_http(self, input_str, verbose=False):
        lines = input_str.split('\r\n')
        if verbose:
            print("-------------------------------")
            for line in lines:
                print(line)
            print("-------------------------------")

        self.path = lines[0]
        self.type = lines[0].split(' ')[0]
        self.path = lines[0].split(' ')[1]
        self.http_v = lines[0].split(' ')[2]

        self.headers = []
        for line in lines[1:]:
            if line != '':
                line_args = line.split(': ')
                self.headers.append(
                    {
                        'key': line_args[0],
                        'value': line_args[1]
                    }
                )

        if self.http_req_to_str() != input_str:
            raise Exception('can not to reapir input str from parsed req')

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
                    rdata.append(sock.recv(self.BUFFER_SIZE).decode())
                except socket.timeout:
                    if len(rdata) == 0:
                        return None
                    else:
                        return ''.join(rdata)

            # unreachable
        finally:
            print('timeout on socket while text parsing')
            sock.settimeout(prev_timeout)

    def recv_data(self, sock):
        prev_timeout = sock.gettimeout()
        try:
            sock.settimeout(0.01)

            data = b''
            # ---------------------------------- read headers ----------------------------------
            while True:
                try:
                    data += sock.recv(self.BUFFER_SIZE)
                except socket.timeout:
                    return data

            # unreachable
        finally:
            print('timeout on socket while data parsing?')
            sock.settimeout(prev_timeout)

    ###############################################################################
    # ----------------------- MAIN STUFF --------------------------------------
    ###############################################################################
    def serve_forever(self):

        parse_only_data = False
        while True:
            self.conn, addr = self.s.accept()
            self.client_addr = addr
            print('Connection address:', self.client_addr)

            is_okay = True
            while is_okay:
                print('reading data from socket')
                if not parse_only_data:
                    rdata = self.recv_text(self.conn)
                self.data = self.recv_data(self.conn)

                parse_only_data = True if self.data == b'' else False

                if not rdata:
                    is_okay = False
                else:
                    self.parst_http(input_str=rdata, verbose=True)
                    print('processing request')
                    self.process_request()

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
            proxy_common_move(self)
            print('GET proceesed, exiting...')
            self.conn.close()
            self.conn.send(self.data)

        elif self.type == 'CONNECT':
            self.send_response(200)
            print('CONNECT processed, keeping connection...')
            self.end_headers()
            self.conn.send(self.data)

        else:
            raise Exception('Undefined method %s' % self.type)


########################################################################################
# ---------------------------------- server via http lib -------------------------------
########################################################################################
class HttpProxyImgCompressor(BaseHTTPRequestHandler):
    def do_GET(self):
        response_content = proxy_common_move(self)
        self.end_headers()

        if response_content is not None:
            self.wfile.write(response_content)
        else:
            print('Bad client address')
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
        r = requests.get(req_res)

        response_content = r.content

        req_handler.send_response(r.status_code)

        for keyword, value in dict(r.headers).items():
            # print("%s:%s" % (keyword, value))
            if keyword.lower() == 'content-type':

                print('content-type:%s' % value)
                req_handler.send_header(keyword, value)

                if value.lower() == 'image/png':
                    img = Image.open(BytesIO(r.content))
                    if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                        print("img compressed")
                        img.thumbnail(MAX_IMG_SIZE)
                        response_content = image_to_byte_array(img)
        return response_content

    else:
        return None
