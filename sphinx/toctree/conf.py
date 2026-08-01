import os
import sys

sys.path.insert(0, os.path.abspath('_extensions'))

project = 'toctree'
copyright = '2026, Kayce Basques'
author = 'Kayce Basques'
version = '0.0.0'
release = '0.0.0'
extensions = ['toctree']
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.venv']
html_theme = 'alabaster'
html_static_path = ['_static']

html_sidebars = {
    '**': [
        'localtoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
        'custom_nav.html',
    ]
}
