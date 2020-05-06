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
# -------------------------------------- stub classes ------------------------------------------------------------------
########################################################################################################################
class SimpleResponse():
    def __init__(self, path, headers, data):
        self.path = path
        self.http_v = path.split(' ')[0]
        self.status_code = int(path.split(' ')[1])
        self.status_str = path.split(' ')[2]
        self.headers = headers
        self.content = data


########################################################################################################################
# -------------------------------------- socket stuff ------------------------------------------------------------------
########################################################################################################################
def parse_http(input_str, verbose):
    def http_resp_to_str():
        res = "%s\r\n" % (path)
        for key, value in headers.items():
            res += "%s: %s\r\n" % (key, value)
        res += '\r\n'
        return res

    lines = input_str.split('\r\n')
    verbose_print(function=whoami(), message='parsing http body')
    if verbose:

        print("---------------------------------------")
        print("----------- HTTP ----------------------")
        print("---------------------------------------")
        for line in lines:
            print(line)
        print("---------------------------------------")
        print("----------- HTTP END ------------------")
        print("---------------------------------------")

    path = lines[0]
    if path == '':
        raise Exception('empty path in parse http')

    headers = {}
    for line in lines[1:]:
        if line != '':
            line_args = line.split(': ')
            headers[line_args[0]] = line_args[1]

    # if http_resp_to_str() != input_str:
    #     raise Exception('can not to repair input str from parsed req')
    # else:
    #     verbose_print(function=whoami(), message='body repaired from fields, test passed')
    return path, headers


def recv_all_data(sock):
    prev_timeout = sock.gettimeout()
    full_data = b''
    try:
        verbose_print(function=whoami(), message='setting timeout in data read')
        sock.settimeout(5)
        verbose_print(function=whoami(), message='timeout seted in data read')
        # ---------------------------------- read headers ----------------------------------
        path = headers = data = None
        try:
            while True:
                next_byte = sock.recv(1)
                full_data += next_byte
                if len(full_data) == 0:
                    break
                if full_data[-1] == 10 \
                        and full_data[-2] == 13 \
                        and full_data[-3] == 10 \
                        and full_data[-4] == 13:
                    break
            verbose_print(whoami(), 'all body readed, parsing http')
            path, headers = parse_http(input_str=full_data.decode(), verbose=True)
            data = b''
            if 'Content-Length' in headers.keys():
                while int(headers['Content-Length']) > len(data):
                    verbose_print(whoami(), 'CONTENT-LEN = %s,DATA.LEN = %d' % (headers['Content-Length'], len(data)))
                    data += sock.recv(int(headers['Content-Length']))

            return path, headers, data
        except socket.timeout:
            return None, None, None


    # unreachable
    finally:
        verbose_print(function=whoami(), message='final block called')
        sock.settimeout(prev_timeout)


########################################################################################################################
# ------------------------------------------------ get request sender --------------------------------------------------
########################################################################################################################
def headers_to_str(headers):
    return ''.join(map(lambda key: "%s: %s\r\n" % (key, headers[key]), headers))


def simple_get(url):
    for i in range(5):
        verbose_print(whoami(), '%d try' % i)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        protocol = url[:4]
        url_req = '/'.join(url[7:].split('/')[1:])
        address = url[7:].split('/')[0]

        s.connect((address, 80))
        default_headers = {
            'Host': str(address),
            'User-Agent': 'python',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }

        s.send(('GET /%s HTTP/1.0\r\n%s\r\n' % (url_req, headers_to_str(default_headers))).encode())

        path, headers, data = recv_all_data(sock=s)

        if headers == None:
            verbose_print(whoami(), 'bad response got')
            continue

        return SimpleResponse(path, headers, data)


########################################################################################################################
# ------------------------------------------------ server --------------------------------------------------------------
########################################################################################################################
class SimpleHttpServer():
    def __init__(self, TCP_IP='', TCP_PORT=8080):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((TCP_IP, TCP_PORT))
        self.s.listen(1)

    ###############################################################################
    # ----------------------- api emulating part -----------------------------------
    ###############################################################################
    def send_response(self, code):
        self._body += ('%s %d %s\r\n' % ('HTTP/1.0', code, 'OK'))

    def send_header(self, keyword, value):
        self._body += ('%s: %s\r\n' % (keyword, value))

    def end_headers(self):
        verbose_print(whoami(), 'sending full body')
        self.conn.send((self._body + '\r\n').encode())

    def process_request(self):
        if self.type == 'GET':
            print('GET: getting response content from request processing function')
            resp_content = proxy_common_move(req_handler=self, get_method=simple_get)
            print('GET: response content getted')
            try:
                self.conn.send(resp_content)
                print('GET: response content sended to proxy client')
            except:
                print('GET: can not send response content to proxy client')

            print('GET: proceesed, exiting...')
            self.conn.close()
            print('GET: connection closed')
            print('_____________________________________________________________________________________________\n\n\n')

        elif self.type == 'CONNECT':
            self.send_response(200)
            self.end_headers()
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
            self._body = ''
            print('\n\n\n_____________________________________________________________________________________________')
            verbose_print(function=whoami(),
                          message='new connection %s: %s' % (self.client_address[0], self.client_address[1]))

            is_okay = True
            while is_okay:
                path, self.headers, self.data = recv_all_data(sock=self.conn)

                if self.headers is None:
                    is_okay = False
                    verbose_print(function=whoami(), message='bad request got')
                else:
                    self.type = path.split(' ')[0]
                    self.path = path.split(' ')[1]
                    self.http_v = path.split(' ')[2]
                    self.process_request()
                    is_okay = False
