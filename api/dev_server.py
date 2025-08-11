from http.server import HTTPServer
from get_pfp import handler


def main() -> None:
    host = '127.0.0.1'
    port = 8787
    print(f"Starting dev API server on http://{host}:{port}")
    httpd = HTTPServer((host, port), handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    main()


