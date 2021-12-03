===================
RST Language Server
===================
|license| |version| |supported-versions| |coverage|

RST Language Server implements the server side of the `Language Server Protocol`_ (LSP) for the `reStructuredText`_ markup language.

RST Language Server is intended to be used by text editors implementing the client side of the protocol. See `langserver.org <https://langserver.org/#implementations-client>`_ for a list of implementing clients.

.. _reStructuredText: https://docutils.sourceforge.io/rst.html
.. _Language Server Protocol: https://microsoft.github.io/language-server-protocol/

Features
========
Autocompletion of title adornments

.. image:: https://raw.githubusercontent.com/digitalernachschub/rst-language-server/a4c81b4805d8ea913042c82e73eb8bae56e88c58/assets/autocomplete_title_adornments.webp

Sections reported as symbols in the editor outline

Comparison to other projects
============================

`rst-mode <https://docutils.sourceforge.io/docs/user/emacs.html>`_ is part of the docutils project. It provides a lot of rst-related functionality, such as operations on text blocks or helpers for indentation and section titles. However, rst-mode is exclusive to Emacs.

`chrisjsewell/rst-language-server <https://github.com/chrisjsewell/rst-language-server>`_ is much more fully featured than this project. It provides diagnostic messages, navigation to references and definitions etc.

However, there seems to be no versioning, releases, or packages that can be simply installed by a user. Moreover, Chris's implementation targets Visual Studio Code only, whereas this project tries to support various editors.


`lextm/restructuredtext-antlr <https://github.com/lextm/restructuredtext-antlr>`_ was an attempt to use ANTLR to parse reStructuredText into a custom syntax tree. The project is discontinued and archived.

RST Language Server relies on docutils for parsing and its Abstract Syntax Tree.

Installation and Setup
======================
RST Language Server is available as a package on PyPI and can be installed via `pip`:

.. code:: sh

    $ pip install --user rst-language-server

Kate
----
Using RST Language Server with `Kate`_ requires the `LSP Client Plugin`_. Once the plugin is activated in the settings a new settings symbol named *LSP-Client* appears. Click on the section, select the *User Server Settings* tab and paste the following server configuration.

.. code:: json

    {
        "servers": {
            "rst": {
                "command": ["rst-ls", "--client-insert-text-interpretation=false"],
                "highlightingModeRegex": "^reStructuredText$"
            }
        }
    }

This will start RST Language Server when opening any file that is configured to use the reStructuredText syntax highlighting.

.. _Kate: https://apps.kde.org/kate/
.. _LSP Client Plugin: https://docs.kde.org/stable5/en/kate/kate/kate-application-plugin-lspclient.html

Neovim
------
There are numerous ways to use Language Servers in with Neovim. This setup configuration assumes that you use `nvim-lspconfig`_.

To registers RST Language Server with nvim-lspconfig, add the following lua code before requiring `lspconfig` and calling the corresponding `setup` function of the language server:

.. code::

  -- Register rst-ls with lspconfig
  local configs = require "lspconfig/configs"
  local util = require "lspconfig/util"

  configs.rst_language_server = {
    default_config = {
      cmd = { "rst-ls" },
      filetypes = { "rst" },
      root_dir = util.path.dirname,
    },
    docs = {
      description = [[
  https://github.com/digitalernachschub/rst-language-server
  Server implementation of the Language Server Protocol for reStructuredText.
  ]],
      default_config = {
        root_dir = [[root_pattern(".git")]],
      },
    },
  }

Note that this setup currently `requires Neovim Nightly (0.6). <https://neovim.discourse.group/t/how-to-add-custom-lang-server-without-fork-and-send-a-pr-to-nvim-lspconfig-repo-resolved/1170/1>`_

.. _nvim-lspconfig: https://github.com/neovim/nvim-lspconfig

Emacs
-----
RST Language Server can be used with Emacs via `lsp-mode <https://emacs-lsp.github.io/lsp-mode/>`_. Add the following configuration to your *init.el* in order to start rst-ls in rst-mode:

.. code:: lisp

    (with-eval-after-load 'lsp-mode
      (add-to-list 'lsp-language-id-configuration
        '(rst-mode . "rst")))

    (defcustom lsp-rst-ls-command '("rst-ls")
      "Command to start the RST Language Server."
      :type 'string)

    (require 'lsp-mode)

    (lsp-register-client
      (make-lsp-client :new-connection (lsp-stdio-connection (lambda () lsp-rst-ls-command))
                       :major-modes '(rst-mode)
                       :server-id 'rst-ls))


Is my editor supported?
=======================
RST Language Server can be used with any text editor that implements a Language Client. See `this list <https://langserver.org/#implementations-client>`_ of Language Client implementations.

Feature Matrix
--------------
+------------------------------------+------+--------+--------+
| Feature \\ Editor                  | Kate | Neovim | Emacs  |
+====================================+======+========+========+
| Autocompletion of title adornments | ✔    | ✔      | ✔      |
+------------------------------------+------+--------+--------+
| Section symbols                    | ✔    | ✔ [#]_ | ✔ [#]_ |
+------------------------------------+------+--------+--------+

.. [#] Tested with `Aerial <https://github.com/stevearc/aerial.nvim>`_
.. [#] Tested with `company-mode <https://company-mode.github.io/>`_

Development configuration with Kate
===================================
The RST Language Server is executed as a subprocess of the Language Client. Therefore, if we want to see log output in Kate we need to write the logs to a file using the `--log-file` command line option. We also set the log level to `debug` in order to view the JSON-RPC messages exchanged between client and server. Lastly, we configure the `root` (i.e. the working directory of the executed command) to the directory where our source code lives in and use `poetry run` to execute the code in the Git repository:

.. code:: json

    {
        "servers": {
            "rst": {
                "command": ["poetry", "run", "rst-ls", "--log-file=/tmp/rst-ls.log", "--log-level=debug", "--client-insert-text-interpretation=false"],
                "root": "/path/to/rst-language-server-repo",
                "highlightingModeRegex": "^reStructuredText$"
            }
        }
    }


.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/rst-language-server?style=flat-square
.. |version| image:: https://img.shields.io/pypi/v/rst-language-server?style=flat-square
.. |license| image:: https://img.shields.io/pypi/l/rst-language-server?style=flat-square
.. |coverage| image:: https://img.shields.io/codecov/c/github/digitalernachschub/rst-language-server?style=flat-square
