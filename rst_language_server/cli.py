import logging

import click

from rst_language_server.server import create_server


@click.command("rst-ls")
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False),
    help="Writes log output to the specified file path",
)
def rst_ls(log_file):
    file_handler = logging.FileHandler(filename=log_file)
    pygls_logger = logging.getLogger("pygls")
    pygls_logger.addHandler(file_handler)
    server_ = create_server()
    server_.start_io()


def main():
    rst_ls()
