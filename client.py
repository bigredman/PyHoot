import errno
import os.path
import socket
import urlparse

from . import (base, constants, custom_exceptions, file_object, request,
               services, util)

SUPPORTED_METHODS = ('GET', 'POST')
SERVICES_HEADERS = {}

MIME_MAPPING = {
    '.html': 'text/html',
    '.png': 'image/png',
    '.txt': 'text/plain',
    '.py': 'application/octet-stream'
}

NON_ALLOWED_TYPES = ['xml']

INITIALIZED, SENDING_STATUS, SENDING_DATA, FINISHED, ERROR = range(5)
SERVICES_LIST = {service.NAME: service for service in
                 services.Service.__subclasses__()}

# Argument call can use f(*[dic[arg] for arg in f.__code__.co_varnames if
# arg in dic])


class Client(base.Base):
    """ Client of Server, handle everything by itself
        Variables:
                self._socket = The socket of the client
                self._recv_buff = any data we recieved but hadn't procssed yet
                self._send_buff = All the data that needed to be sent but
                                  hadn't sent yet
                self._buff_size = The buff size of the server
                self._file = FileObject or service object of the file\service
                             the request wants
                self._request = Request object of the request we got
                self._base_directory: The base directory whice we will use for
                                      file locations
    """

    def __init__(
        self,
        s,
        buff_size,
        base_directory,
        server
    ):
        """Client of Server, handle everything by itself
        Arguements:
        s: the socket of this client, CANNOT BE MODIFIED
        buff_size: The buff size of the server
        base_directory: The base directory whice we will use for file locations
        """
        super(Client, self).__init__()
        self._socket = s
        self._buff_size = buff_size
        self._base_directory = base_directory
        self._server = server

        self._file = None
        self._game = None
        self._send_buff = ""
        self._recv_buff = ""
        self._request = None
        self._state = INITIALIZED
        self._game_state = constants.NONE

    def get_socket(self):
        """Get the socket of this client, private arguement"""
        return self._socket

    def _test_http_and_creat_objects(self):
        parsed_lines = self._recv_buff.split(constants.CRLF, 1)
        req = parsed_lines[0].split(' ', 2)
        if req[2] != constants.HTTP_VERSION:
            raise RuntimeError('Not HTTP protocol')
        if len(req) != 3:
            raise RuntimeError('Incomplete HTTP protocol')
        self.logger.debug("Req, %s", req)
        method, uri, signature = req
        if method not in SUPPORTED_METHODS:
            raise RuntimeError("HTTP unspported method '%s'" % method)
        if not uri or uri[0] != '/' or '\\' in uri:
            raise RuntimeError("Invalid URI")
        uri_path = urlparse.urlparse(uri).path
        if uri_path not in SERVICES_LIST.keys():
            file_type = os.path.splitext(uri_path)[1]
            if file_type in NON_ALLOWED_TYPES:
                raise custom_exceptions.AccessDenied()
            self._file = file_object.FileObject(uri_path, self._base_directory)
            self._send_buff += (
                "%s 200 OK\r\n"
                "Content-Length: %s\r\n"
                "Content-Type: %s\r\n"
                "\r\n"
            ) % (
                constants.HTTP_VERSION,
                self._file.get_file_size(),
                MIME_MAPPING.get(file_type),
            )
        else:

            # The service initialzor
            service_function = SERVICES_LIST[uri_path]

            # dictionary of the query of uri
            if method == "GET":
                dic_argument = urlparse.parse_qs(uri.query)
            else:
                dic_argument = urlparse.parse_qs(
                    self._recv_buff.split(constants.DOUBLE_CRLF)[-1]
                )
            # Remove un-usable keys
            dic_argument.pop('self', None)

            # Creat a tupple of the arguments for service_function that
            # are in dic_argument
            self._file = service_function(
                *(dic_argument[arg] for arg in
                  service_function.__init__.__code__.co_varnames if
                  arg in dic_argument)
            )
            self._send_buff += self._file.headers()
        self._request = request.Request(method, uri)
        self.logger.debug("Created file\service and request")
        if len(parsed_lines) == 1:
            self._recv_buff = ""
        else:
            self._recv_buff = parsed_lines[1]
        self._state = SENDING_STATUS

    def _get_headers(self):
        self._recv_data()
        self.logger.debug("after recv lines %s" % self._recv_buff)
        if constants.CRLF in self._recv_buff:
            uri = self._request.get_uri()
            if (
                uri in SERVICES_HEADERS.keys() or
                self._request.get_method == "POST"
            ):
                for line in self._recv_buff.split(constants.CRLF):
                    parsed = line.split(":", 1)
                    if ": " in line and parsed[0] in SERVICES_HEADERS[
                            uri] + ["cookie"]:
                        if len(parsed) == 2:
                            self._request.add_header(*parsed)
                            self.logger.debug("Added header, %s", line)
        self._recv_buff = ""

    def _change_to_error(self, error_messege):
        self._send_buff = error_messege
        self._state = ERROR
        self._recv_buff = ""

    def _set_game(self):
        headers = self._request.get_all_header()
        if "cookie" not in headers:
            # TODO: add a way to add headers for responce

    def recv(self):
        """Recv data from the client socket and process it to Reqeust and
           FileObject, or put it in the buff"""
        try:
            # If there is no request line, get it
            if self._state == INITIALIZED:
                self._recv_data()
                self.logger.debug("after recv %s", self._recv_buff)
            # If we have the request line, but don't have request object, creat
            # one
            if (
                self._state == INITIALIZED
                and constants.CRLF in self._recv_buff
            ):
                self._test_http_and_creat_objects()

            # If we do have request line, get headers

            if self._state in (SENDING_DATA, SENDING_STATUS):
                self._get_headers()
            if urlparse.urlparse(self._request.get_uri).path in SERVICES_LIST:
                self._set_game()
            self.logger.debug("Now recv_buff is %s" % self._recv_buff)

        except OSError as e:
            self.logger.error('Exception ', exc_info=True)
            if e.errno == errno.ENOENT:
                self._change_to_error(
                    util.creat_error(
                        404, 'File Not Found', e))
            else:
                self._change_to_error(
                    util.creat_error(
                        500, 'Internal Error', e))
        except custom_exceptions.AccessDenied as e:
            self.logger.error('Exception ', exc_info=True)
            self._change_to_error(util.creat_error(403, 'Forbidden', e))
        except Exception as e:
            self.logger.error('Exception ', exc_info=True)
            self._change_to_error(util.creat_error(500, 'Internal Error', e))

    def send(self):
        """ Fill self.send_buff with all the data it needs and then send it
        """
        if self._state == ERROR:
            self._send_my_buff()
            if self._send_buff == "":
                self._state = FINISHED
        if self._state == SENDING_STATUS:
            if self._send_buff:
                self._send_my_buff()
            else:
                self._state = SENDING_DATA
        if self._state == SENDING_DATA:
            if self._send_buff == "" and self._file is not None:
                r = self._file.read_buff(self._buff_size)
                self._send_buff += r
                if len(r) < self._buff_size:
                    self._file.finished_reading = True
            if self._send_buff != "":
                self._send_my_buff()
            if self._file is not None and self._file.finished_reading:
                self._state = FINISHED

    def check_finished_request(self):
        """Check if we finished the request"""
        return self._state == FINISHED

    def _send_my_buff(self):
        """Send the data in self._send_buff"""
        self.logger.debug("start sending my buff, send_buff %s" %
                          self._send_buff)
        try:
            while self._send_buff:
                self._send_buff = self._send_buff[
                    self._socket.send(self._send_buff):]
                self.logger.debug("client sent")
        except socket.error as e:
            if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
        self.logger.debug("Sent all that I could, send_buff %s" %
                          self._send_buff)

    def get_send_buff(self):
        """Return _send_buff"""
        return self._send_buff

    def _recv_data(
        self,
        max_length=constants.MAX_HEADER_LENGTH,
        block_size=constants.BUFF_SIZE,
    ):
        """Recive data from socket s, if unable return how much it did read"""
        try:
            self.logger.debug("_recv_data %s", self._recv_buff)
            while True:
                n = self._recv_buff.find(constants.CRLF)
                if n != -1:
                    break
                t = self._socket.recv(block_size)
                if not t:
                    raise custom_exceptions.Disconnect()
                self._recv_buff += t
        except socket.error as e:
            if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise

    def can_recv(self):
        """Decide if it can recive more data or not"""
        ans = len(self._recv_buff) < self._buff_size
        if self._request is not None:
            ans = ans and not self._request.full_request
        return ans

    def can_send(self):
        return (
            len(self._send_buff) > 0 or
            self._state in (SENDING_DATA, SENDING_STATUS)
        )

    def get_file(self):
        """Return self._file"""
        return self._file
