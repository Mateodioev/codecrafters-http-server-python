import socket
import re

CRLF_DELIMITER = "\r\n"
HTTP_VERSION = "HTTP/1.1"


class RequestContent():
    def __init__(self, *, method: str, path: str, http_version: str, headers: dict, body: str) -> None:
        self.method = method
        self.path = path
        self.http_version = http_version
        self.headers = headers
        self.body = body

    def header(self, key: str) -> str:
        return ', '.join(self.headers_pair(key))

    def headers_pair(self, key: str) -> tuple:
        """
        Returns the key-value pair of the header with the given key.
        """
        return self.headers.get(key.lower()) or ()

    def to_encoded_request(self) -> str:
        headers_line = f"{self.method} {self.path} {self.http_version}"
        general_headers = CRLF_DELIMITER.join(
            [f"{key}: {', '.join(value)}" for key,
             value in self.headers.items()]
        )

        return f"{headers_line}{CRLF_DELIMITER}{general_headers}{CRLF_DELIMITER}{self.body}"

    def __bytes__(self) -> bytes:
        return self.to_encoded_request().encode()

    def __str__(self) -> str:
        return f"RequestContent(method={self.method}, url={self.path}, http_version={self.http_version}, headers={self.headers}, body={self.body})"


class RequestParser():
    def __init__(self, body: str):
        self.body = body

    def parse(self) -> RequestContent:
        headers, body = self.body.split(CRLF_DELIMITER * 2)
        headers = headers.split(CRLF_DELIMITER)

        # First line is the request line
        request_line = headers.pop(0)
        # Split the request line into method, url and http_version
        method, url, http_version = request_line.split(" ")

        # Parse the headers
        headers_dict = {}
        for header in headers:
            key, value = header.split(": ", maxsplit=2)
            headers_dict[key.lower()] = tuple(value.split(", "))
            # This is RFC 2616 compliant, but we don't need to worry about multiple headers with the same key

        return RequestContent(
            method=method,
            path=url,
            http_version=http_version,
            headers=headers_dict,
            body=body
        )


class ResponseContent():
    def __init__(self) -> None:
        self.headers = {}
        self.body = ""
        self.status_code = 200
        self.reason_phrase = "OK"

    @staticmethod
    def not_found():
        return ResponseContent() \
            .set_status_code(404, "Not Found") \
            .set_body("Not Found")

    def set_header(self, key: str, value: str):
        return self.set_header_pair(key, (value,))

    def set_header_pair(self, key: str, values: tuple):
        self.headers[key] = values
        return self

    def set_content_type(self, content_type: str):
        return self.set_header("Content-Type", content_type)

    def set_status_code(self, status_code: int, reason_phrase: str = "OK"):
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        return self

    def set_body(self, body: str):
        self.body = body
        return self

    def to_encoded_response(self) -> str:
        if self.headers.get("Content-Type") is None:
            self.set_content_type("text/plain")
        self.set_header("Content-Length", str(len(self.body)))

        status_line = f"{HTTP_VERSION} {self.status_code} {self.reason_phrase}"
        general_headers = CRLF_DELIMITER.join(
            [f"{key}: {', '.join(value)}" for key,
             value in self.headers.items()]
        )
        return f"{status_line}{CRLF_DELIMITER}{general_headers}{CRLF_DELIMITER*2}{self.body}"

    def __bytes__(self) -> bytes:
        return self.to_encoded_response().encode()


class Route():
    def __init__(self, path: str, callback) -> None:
        """
        Represents a route in the server.

        :param path: The path of the route (e.g. /, /about, /echo/{user})
        :param callback: The callback function to be called when the route is matched
        """
        self.path = path
        self.callback = callback
        self.pattern = self._build_pattern()
        self.args = []

    def match(self, path: str) -> bool:
        """
        Checks if the given path matches the route.
        """
        match = re.match(self.pattern, path)
        if match:
            self.args = match.groups()
            return True
        return False

    def _build_pattern(self):
        """
        Builds a regex pattern from the path.
        """
        if self.path == "/":
            return r"^/$"
        return re.sub(r"{(\w+)}", r"([^/]+)", self.path)


class ServerSocket():
    def __init__(self, host: str, port: int):
        self.socket = socket.create_server((host, port), reuse_port=True)
        self.router = {
            "GET": [],
            "POST": [],
            "PUT": [],
            "DELETE": [],
            # Add more methods if needed
        }

    def on(self, method: str, path: str, callback) -> None:
        self.router[method.upper()].append(Route(path, callback))

    def run(self) -> None:
        self.socket.listen()
        while True:
            client, _ = self.socket.accept()
            data = client.recv(2048).decode()
            request = RequestParser(data).parse()

            # In need to move this to a function
            if request.method in self.router:
                routes = self.router[request.method]
                for route in routes:
                    if route.match(request.path):
                        response = route.callback(request, *route.args)
                        client.send(bytes(response))
                        break
                else:
                    client.send(bytes(ResponseContent.not_found()))

                client.close()

    def close(self):
        self.socket.close()


def index_route(request: RequestContent, *args) -> ResponseContent:
    return ResponseContent().set_body("Hello, World!: ")


def echo_route(request: RequestContent, *args) -> ResponseContent:
    return ResponseContent().set_body(args[0])


def user_agent_route(request: RequestContent, *args) -> ResponseContent:
    return ResponseContent() \
        .set_body(request.header("UsEr-aGeNT"))


def main():
    server = ServerSocket("localhost", 4221)

    server.on("GET", "/echo/{str}", echo_route)
    server.on("GET", "/user-agent", user_agent_route)
    server.on("GET", "/", index_route)
    server.run()
    server.close()


if __name__ == "__main__":
    main()
