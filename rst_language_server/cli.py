import logging

import click

from rst_language_server.server import create_server

_log_level_names = [
    logging.getLevelName(level).lower()
    for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
]


@click.command("rst-ls")
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False),
    help="Writes log output to the specified file path",
)
@click.option(
    "--log-level",
    type=click.Choice(_log_level_names),
    default="info",
    help="Sets the minimum severity for log output",
)
def rst_ls(log_file, log_level: str):
    file_handler = logging.FileHandler(filename=log_file)
    pygls_logger = logging.getLogger("pygls")
    pygls_logger.setLevel(log_level.upper())
    pygls_logger.addHandler(file_handler)
    server_ = create_server()
    server_.start_io()


def main():
    rst_ls()
