===================
RST Language Server
===================
RST Language Server implements the server side of the `Language Server Protocol`_ (LSP) for the `reStructuredText`_ markup language.

RST Language Server is intended to be used by text editors implementing the client side of the protocol. See `langserver.org <https://langserver.org/#implementations-client>`_ for a list of implementing clients.

.. _reStructuredText: https://docutils.sourceforge.io/rst.html
.. _Language Server Protocol: https://microsoft.github.io/language-server-protocol/

Features
========
Autocompletion of title adornments

.. image:: https://raw.githubusercontent.com/digitalernachschub/rst-language-server/a4c81b4805d8ea913042c82e73eb8bae56e88c58/assets/autocomplete_title_adornments.webp

Installation
============
RST Language Server is available as a package on PyPI and can be installed via `pip`:

.. code:: sh

    $ pip install --user rst-language-server

Usage with Kate
===============

Using RST Language Server with `Kate`_ requires the `LSP Client Plugin`_. Once the plugin is activated in the settings a new settings symbol named *LSP-Client* appears. Click on the section, select the *User Server Settings* tab and paste the following server configuration.

.. code:: json

    {
        "servers": {
            "rst": {
                "command": ["rst-ls"],
                "highlightingModeRegex": "^reStructuredText$"
            }
        }
    }

This will start RST Language Server when opening any file that is configured to use the reStructuredText syntax highlighting.

.. _Kate: https://apps.kde.org/kate/
.. _LSP Client Plugin: https://docs.kde.org/stable5/en/kate/kate/kate-application-plugin-lspclient.html


Is my editor supported?
=======================
RST Language Server can be used with any text editor that implements a Language Client. See `this list <https://langserver.org/#implementations-client>`_ of Language Client implementations.


Development configuration with Kate
===================================
The RST Language Server is executed as a subprocess of the Language Client. Therefore, if we want to see log output in Kate we need to write the logs to a file using the `--log-file` command line option. We also set the log level to `debug` in order to view the JSON-RPC messages exchanged between client and server. Lastly, we configure the `root` (i.e. the working directory of the executed command) to the directory where our source code lives in and use `poetry run` to execute the code in the Git repository:

.. code:: json

    {
        "servers": {
            "rst": {
                "command": ["poetry", "run", "rst-ls", "--log-file=/tmp/rst-ls.log", "--log-level=debug"],
                "root": "/path/to/rst-language-server-repo",
                "highlightingModeRegex": "^reStructuredText$"
            }
        }
    }
