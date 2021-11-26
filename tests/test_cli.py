import logging
from unittest.mock import patch

from click.testing import CliRunner

from rst_language_server.cli import rst_ls


def test_help_option_shows_help():
    cli = CliRunner()

    result = cli.invoke(rst_ls, ["--help"])

    assert result.exit_code == 0
    assert result.stdout


def test_log_file_option_configures_file_for_pygls(tmp_path):
    cli = CliRunner()
    log_file = tmp_path / "output.log"

    with patch("rst_language_server.server.create_server"):
        cli.invoke(rst_ls, [f"--log-file={str(log_file)}"])

    logger = logging.getLogger("pygls")
    file_handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, logging.FileHandler)
    ]
    assert file_handlers
    file_handler = file_handlers[0]
    assert file_handler.baseFilename == str(log_file)
