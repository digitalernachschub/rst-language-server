from click.testing import CliRunner

from rst_language_server.cli import rst_ls


def test_help_option_shows_help():
    cli = CliRunner()

    result = cli.invoke(rst_ls, ["--help"])

    assert result.exit_code == 0
    assert result.stdout
