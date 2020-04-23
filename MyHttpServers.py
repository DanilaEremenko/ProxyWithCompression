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

    def start_server(self):

        while True:
            conn, addr = self.s.accept()
            print('Connection address:', addr)

            is_okay = True
            while is_okay:
                data = conn.recv(self.BUFFER_SIZE)
                if not data:
                    is_okay = False
                else:
                    lines = data.decode().split('\r\n')

                    print("-------------------------------")
                    for line in lines:
                        print(line)
                    print("-------------------------------")

                    conn.send(data)  # echo

            conn.close()


########################################################################################
# ---------------------------------- via http lib --------------------------------------
########################################################################################
class HttpProxyImgCompressor(BaseHTTPRequestHandler):
    def do_GET(self):
        def image_to_byte_array(image):
            imgByteArr = BytesIO()
            image.save(imgByteArr, format=image.format)
            imgByteArr = imgByteArr.getvalue()
            return imgByteArr

        if self.client_address[0] in CLIENT_LIST:
            req_res = self.path
            print('requested resource %s' % req_res)
            r = requests.get(req_res)

            response_content = r.content

            self.send_response(r.status_code)

            for keyword, value in dict(r.headers).items():
                # print("%s:%s" % (keyword, value))
                if keyword.lower() == 'content-type':

                    print('content-type:%s' % value)
                    self.send_header(keyword, value)

                    if value.lower() == 'image/png':
                        img = Image.open(BytesIO(r.content))
                        if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                            print("img compressed")
                            img.thumbnail(MAX_IMG_SIZE)
                            response_content = image_to_byte_array(img)

            self.end_headers()

            self.wfile.write(response_content)

        elif self.client_address[0] not in CLIENT_LIST:
            print('Bad client address')
            self._send_bad_client_response()
        else:
            print('Unreachable state wha???')
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
