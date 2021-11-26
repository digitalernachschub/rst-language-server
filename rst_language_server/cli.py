from rst_language_server.server import create_server


def main():
    server_ = create_server()
    server_.start_io()
