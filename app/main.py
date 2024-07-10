import socket

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
        """
        Returns the first value of the header with the given key.
        """
        return self.headers.get(key)[0] or ""

    def headers_pair(self, key: str) -> tuple:
        """
        Returns the key-value pair of the header with the given key.
        """
        return self.headers.get(key) or ()

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
            headers_dict[key] = tuple(value.split(", "))
            # This is RFC 2616 compliant, but we don't need to worry about multiple headers with the same key

        return RequestContent(
            method=method,
            path=url,
            http_version=http_version,
            headers=headers_dict,
            body=body
        )


def create_response_body(status_code: int = 200, reason_phrase: str = "OK", headers: dict = {}, body: str = "", http_version: str = HTTP_VERSION) -> str:
    response = f"{http_version} {status_code} {reason_phrase}{CRLF_DELIMITER}"
    for key, value in headers.items():
        response += f"{key}: {value}{CRLF_DELIMITER}"
    response += CRLF_DELIMITER
    response += body
    return response


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client, addr = server_socket.accept()  # wait for client

    # receive data from client
    data = client.recv(2048).decode()
    request = RequestParser(data).parse()

    if request.path == "/":
        client.sendall(create_response_body().encode())
    else:
        client.sendall(create_response_body(
            status_code=404,
            reason_phrase="Not Found"
        ).encode())


if __name__ == "__main__":
    main()
