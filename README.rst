===================
RST Language Server
===================
RST Language Server implements the server side of the `Language Server Protocol`_ (LSP) for the `reStructuredText`_ markup language.

RST Language Server is intended to be used by text editors implementing the client side of the protocol. See `langserver.org <https://langserver.org/#implementations-client>`_ for a list of implementing clients.

.. _reStructuredText: https://docutils.sourceforge.io/rst.html
.. _Language Server Protocol: https://microsoft.github.io/language-server-protocol/

Testing with Kate
=================

Using RST Language Server with `Kate`_ requires the `LSP Client Plugin`_. Once the plugin is activated in the settings a new settings symbol named *LSP-Client* appears. Click on the section, select the *User Server Settings* tab and paste the following server configuration.

.. code:: json

    {
        "servers": {
            "rst": {
                "command": ["poetry", "run", "python", "-m", "rst_language_server"],
                "root": "/path/to/rst-language-server-repo",
                "highlightingModeRegex": "^reStructuredText$"
            }
        }
    }

This will start RST Language Server when opening any file that is configured to use the reStructuredText syntax highlighting.

.. _Kate: https://apps.kde.org/kate/
.. _LSP Client Plugin: https://docs.kde.org/stable5/en/kate/kate/kate-application-plugin-lspclient.html
