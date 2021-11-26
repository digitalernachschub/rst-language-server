import click

from rst_language_server.server import create_server


@click.command("rst-ls")
def rst_ls():
    server_ = create_server()
    server_.start_io()


def main():
    rst_ls()
