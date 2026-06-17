"""Sphinx configuration for conda-completion documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = html_title = "conda-completion"
copyright = "2025, Jannis Leidel"
author = "Jannis Leidel"

extensions = [
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

html_theme = "conda_sphinx_theme"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/conda-incubator/conda-completion",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
}

html_context = {
    "github_user": "conda-incubator",
    "github_repo": "conda-completion",
    "github_version": "main",
    "doc_path": "docs",
}

html_extra_path = ["robots.txt"]

html_baseurl = "https://conda-incubator.github.io/conda-completion/"

exclude_patterns = ["_build"]

intersphinx_mapping = {
    "conda": ("https://docs.conda.io/projects/conda/en/latest/", None),
}
intersphinx_timeout = 10
