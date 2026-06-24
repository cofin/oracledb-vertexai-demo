# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Sphinx configuration for the Cymbal Coffee learning portal."""

project = "Cymbal Coffee"
project_copyright = "2026, Google LLC"
author = "Google LLC"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_immaterial",
    "sphinxcontrib.mermaid",
]

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "screenshots/**"]
nitpicky = False

myst_enable_extensions = ["attrs_block", "colon_fence", "deflist", "fieldlist", "linkify", "substitution", "tasklist"]
myst_heading_anchors = 3

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_class_signature = "separated"
autodoc_default_options = {"members": True, "show-inheritance": True, "undoc-members": False}
napoleon_google_docstring = True
napoleon_numpy_docstring = False

html_theme = "sphinx_immaterial"
html_title = ""
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/cymbal-coffee-logo.svg"
html_favicon = "_static/cymbal-coffee-cup.svg"
html_theme_options = {
    "site_url": "https://cofin.github.io/oracledb-vertexai-demo/",
    "repo_url": "https://github.com/cofin/oracledb-vertexai-demo",
    "repo_name": "oracledb-vertexai-demo",
    "edit_uri": "edit/main/docs",
    "globaltoc_collapse": False,
    "icon": {"repo": "fontawesome/brands/github"},
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "green",
            "accent": "amber",
            "toggle": {"icon": "material/lightbulb", "name": "Switch to dark mode"},
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "green",
            "accent": "amber",
            "toggle": {"icon": "material/lightbulb-outline", "name": "Switch to light mode"},
        },
    ],
    "features": [
        "content.code.annotate",
        "content.code.copy",
        "content.tabs.link",
        "navigation.expand",
        "navigation.footer",
        "navigation.instant",
        "navigation.sections",
        "navigation.top",
        "navigation.tracking",
        "search.highlight",
        "search.share",
        "search.suggest",
        "toc.follow",
        "toc.sticky",
    ],
    "version_dropdown": False,
    "social": [
        {
            "icon": "fontawesome/brands/github",
            "link": "https://github.com/cofin/oracledb-vertexai-demo",
            "name": "Source on GitHub",
        }
    ],
}

sphinx_immaterial_custom_admonitions = [
    {
        "name": "tour-stop",
        "title": "Tour stop",
        "icon": "material/map-marker-path",
        "color": (217, 119, 6),
        "classes": ["note"],
    },
    {
        "name": "oracle-internals",
        "title": "Oracle 26ai internals",
        "icon": "material/database",
        "color": (197, 17, 0),
        "classes": ["info"],
    },
    {
        "name": "agent-detail",
        "title": "ADK 2.0 detail",
        "icon": "material/robot-outline",
        "color": (66, 133, 244),
        "classes": ["info"],
    },
]

mermaid_version = "11.4.1"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "litestar": ("https://docs.litestar.dev/2/", None),
}
