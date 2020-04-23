import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import signal
import sys
import requests
from io import BytesIO
from PIL import Image

MAX_IMG_SIZE = (64, 64)


class HttpProxyImgCompressor(BaseHTTPRequestHandler):
    def do_GET(self):
        def image_to_byte_array(image):
            imgByteArr = BytesIO()
            image.save(imgByteArr, format=image.format)
            imgByteArr = imgByteArr.getvalue()
            return imgByteArr

        if self.client_address[0] == '127.0.0.1':
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

        elif self.client_address[0] != '127.0.0.1':
            print('Bad client address')
            self._send_bad_client_response()
        else:
            print('Unreachable state wha???')
            self._send_bad_client_response()

        print("-------------------------------------")

    def do_CONNECT(self):
        if self.client_address[0] == '127.0.0.1':
            self.send_response(200)
            print('localhost connected')

    def _send_bad_client_response(self):
        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<h1>Sorry bro<h1>")


def signal_handler(sig, frame):
    print('Exiting server')
    sys.exit(0)


def main():
    # parsing arguments
    parser = argparse.ArgumentParser(description="Simple http server with optional -p flag")
    parser.add_argument("-p", "--port", type=int, action="store", help="port")
    args = parser.parse_args()
    port = args.port if args.port is not None else 8080

    # running server
    print("Starting HttpProxyImgCompressor server...")

    signal.signal(signal.SIGINT, signal_handler)
    print("SIGINT handler created")

    serv = HTTPServer(('', port), HttpProxyImgCompressor)
    print("Requests expected on %d port\nRunning server..." % port)
    print("-------------------------------------")

    serv.serve_forever()


if __name__ == '__main__':
    main()
