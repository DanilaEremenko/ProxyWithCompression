from MyHttpServers import HttpProxyImgCompressor

import argparse
from http.server import HTTPServer
import signal
import sys


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
