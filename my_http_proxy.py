import inspect
import socket
import requests

from common_part import proxy_common_move


########################################################################################################################
# --------------------------------------- versbosity -------------------------------------------------------------------
########################################################################################################################
def verbose_print(function, message):
    print("--%s: %s" % (function.upper(), message))


def whoami():
    return inspect.stack()[1][3]


########################################################################################################################
# ------------------------------------------------ server --------------------------------------------------------------
########################################################################################################################
class SimpleHttpServer():
    def __init__(self, TCP_IP='', TCP_PORT=8080, BUFFER_SIZE=1024):
        self.BUFFER_SIZE = BUFFER_SIZE  # Normally 1024, but we want fast response
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((TCP_IP, TCP_PORT))
        self.s.listen(1)

    ###############################################################################
    # ----------------------- socket stuff --------------------------------------
    ###############################################################################
    def recv_text(self, sock):
        r'''Receive everything from `sock`, until timeout occurs, meaning sender
        is exhausted, return result as string.'''

        # dirty hack to simplify this stuff - you should really use zero timeout,
        # deal with async socket and implement finite automata to handle incoming data

        prev_timeout = sock.gettimeout()
        rdata = []
        try:
            verbose_print(function=whoami(), message='setting timeout in text read')
            sock.settimeout(0.01)
            verbose_print(function=whoami(), message='timeout seted in text read')
            # ---------------------------------- read headers ----------------------------------
            while True:
                try:
                    verbose_print(function=whoami(), message='reading text chunk')
                    rdata.append(sock.recv(self.BUFFER_SIZE).decode())
                    verbose_print(function=whoami(), message='text chunk readed')
                    if rdata[0][-4:] == '\r\n\r\n':
                        verbose_print(function=whoami(), message='all text readed, next go to the data reading')
                        return ''.join(rdata)
                except socket.timeout:
                    if len(rdata) == 0:
                        verbose_print(function=whoami(), message='empty rdata array got')
                        return None
                    else:
                        verbose_print(function=whoami(), message='rdata returned')
                        return ''.join(rdata)

            # unreachable
        finally:
            verbose_print(function=whoami(), message='unreachable timeout on socket while data parsing?')
            sock.settimeout(prev_timeout)

    def recv_data(self, sock):
        prev_timeout = sock.gettimeout()
        data = b''
        try:
            verbose_print(function=whoami(), message='setting timeout in data read')
            sock.settimeout(0.01)
            verbose_print(function=whoami(), message='timeout seted in data read')
            # ---------------------------------- read headers ----------------------------------
            while True:
                try:
                    verbose_print(function=whoami(), message='reading data chunk')
                    new_data = sock.recv(self.BUFFER_SIZE)
                    verbose_print(function=whoami(), message='data chunk readed')
                    data += new_data
                    verbose_print(function=whoami(), message='data chunks joined')

                except socket.timeout:
                    verbose_print(function=whoami(), message='data returned')
                    return data

            # unreachable
        finally:
            verbose_print(function=whoami(), message='unreachable timeout on socket while data parsing?')
            sock.settimeout(prev_timeout)
            return data

    ###############################################################################
    # ----------------------- parsing stuff --------------------------------------
    ###############################################################################
    def parse_http_req(self, input_str, verbose):
        lines = input_str.split('\r\n')
        verbose_print(function=whoami(), message='parsing http body')
        if verbose:
            print("---------------------------------------")
            print("------------- REQUEST -----------------")
            print("---------------------------------------")

            for line in lines:
                print(line)
            print("---------------------------------------")
            print("------------- END REQUEST -------------")
            print("---------------------------------------")

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
            verbose_print(function=whoami(), message='body repaired from fields, test passed')

    def http_req_to_str(self):
        res = "%s %s %s\r\n" % (self.type, self.path, self.http_v)
        for key, value in self.headers.items():
            res += "%s: %s\r\n" % (key, value)
        res += '\r\n'
        return res

    ###############################################################################
    # ----------------------- api emulating part -----------------------------------
    ###############################################################################
    def send_response(self, code):
        self.conn.send(('%s %d %s' % ('HTTP/1.1', code, 'OK')).encode())

    def send_header(self, keyword, value):
        self.conn.send(('%s: %s\n' % (keyword, value)).encode())

    def end_headers(self):
        self.conn.send('\r\n'.encode())

    def process_request(self):
        if self.type == 'GET':
            print('GET: getting response content from request processing function')
            response_content = proxy_common_move(req_handler=self, get_method=requests.get)
            print('GET: response content getted')
            try:
                self.conn.send(response_content)
                print('GET: response content sended to proxy client')
            except:
                print('GET: can not send response content to proxy client')

            print('GET: proceesed, exiting...')
            # if self.headers['Proxy-Connection'] == 'keep-alive':
            #     print('GET: connection keeped')
            # else:
            #     self.conn.close()
            #     print('GET: connection closed')
            self.conn.close()
            print('GET: connection closed')
            print('_____________________________________________________________________________________________\n\n\n')

        elif self.type == 'CONNECT':
            self.send_response(200)
            print('CONNECT processed, keeping connection...')
            print('_____________________________________________________________________________________________\n\n\n')

        else:
            raise Exception('Undefined method %s' % self.type)

    ###############################################################################
    # ----------------------- MAIN STUFF --------------------------------------
    ###############################################################################
    def serve_forever(self):
        while True:
            self.conn, self.client_address = self.s.accept()
            print('\n\n\n_____________________________________________________________________________________________')
            verbose_print(function=whoami(),
                          message='new connection %s: %s' % (self.client_address[0], self.client_address[1]))

            is_okay = True
            while is_okay:
                self.rdata = self.recv_text(self.conn)
                if not self.rdata:
                    is_okay = False
                    verbose_print(function=whoami(), message='rdata is not, exiting...')
                else:
                    self.parse_http_req(input_str=self.rdata, verbose=True)

                    if 'Content-Length' in self.headers.keys():
                        verbose_print(function=whoami(),
                                      message='Content-Length = %s found' % self.headers['Content-Length'])
                        self.data = self.recv_data(self.conn)
                    else:
                        verbose_print(function=whoami(), message='no Content-Length key in headers')

                    self.process_request()
                    is_okay = False
