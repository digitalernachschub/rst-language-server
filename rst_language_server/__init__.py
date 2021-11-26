__version__ = "0.1.0"

from rst_language_server.server import create_server

__all__ = ["create_server"]


def main():
    server_ = create_server()
    server_.start_io()
