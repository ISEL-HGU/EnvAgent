"""
Helper utility functions for EnvAgent.
"""

import re
from typing import Set


def sanitize_env_name(name: str) -> str:
    """
    Convert project name to valid conda environment name.

    Conda environment names must:
    - Not contain spaces
    - Not contain special characters like #, /, :, @, etc.
    - Be lowercase (convention)
    - Not start/end with underscores

    Args:
        name: Original project name

    Returns:
        Sanitized environment name safe for conda

    Examples:
        >>> sanitize_env_name("ML Test Project")
        'ml_test_project'
        >>> sanitize_env_name("My-App@v2.0")
        'my_app_v2_0'
        >>> sanitize_env_name("project#123")
        'project_123'
    """
    if not name or not name.strip():
        return 'env'

    # Replace spaces and hyphens with underscores
    name = name.replace(' ', '_').replace('-', '_')

    # Remove invalid characters (keep only alphanumeric and underscores)
    # This removes: #, /, :, @, !, $, %, ^, &, *, (, ), etc.
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)

    # Convert to lowercase
    name = name.lower()

    # Remove consecutive underscores
    while '__' in name:
        name = name.replace('__', '_')

    # Strip leading/trailing underscores
    name = name.strip('_')

    # Ensure we have a valid name
    if not name:
        return 'env'

    # Ensure it starts with a letter (conda requirement)
    if name[0].isdigit():
        name = 'env_' + name

    return name


# Import name to package name mapping
IMPORT_TO_PACKAGE = {
    # Common mismatches between import name and package name
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'sklearn': 'scikit-learn',
    'skimage': 'scikit-image',
    'yaml': 'pyyaml',
    'dotenv': 'python-dotenv',
    'bs4': 'beautifulsoup4',
    'dateutil': 'python-dateutil',
    'magic': 'python-magic',
    'OpenSSL': 'pyopenssl',
    'serial': 'pyserial',
    'usb': 'pyusb',
    'lxml.etree': 'lxml',
    'pytest': 'pytest',
    'flask': 'flask',
    'django': 'django',
    'fastapi': 'fastapi',
    'torch': 'pytorch',
    'torchvision': 'torchvision',
    'torchaudio': 'torchaudio',
    'tensorflow': 'tensorflow',
    'keras': 'keras',
    'jax': 'jax',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'scipy': 'scipy',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'plotly': 'plotly',
    'streamlit': 'streamlit',
    'gradio': 'gradio',
    'transformers': 'transformers',
    'datasets': 'datasets',
    'tokenizers': 'tokenizers',
    'accelerate': 'accelerate',
    'diffusers': 'diffusers',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'langchain': 'langchain',
    'llama_index': 'llama-index',
    'chromadb': 'chromadb',
    'pinecone': 'pinecone-client',
    'sqlalchemy': 'sqlalchemy',
    'pymongo': 'pymongo',
    'redis': 'redis',
    'celery': 'celery',
    'requests': 'requests',
    'httpx': 'httpx',
    'aiohttp': 'aiohttp',
    'websocket': 'websocket-client',
    'pydantic': 'pydantic',
    'typer': 'typer',
    'click': 'click',
    'rich': 'rich',
    'tqdm': 'tqdm',
    'loguru': 'loguru',
}


def extract_imports(code: str) -> Set[str]:
    """
    Extract all import statements from Python code.

    Args:
        code: Python source code as string

    Returns:
        Set of imported module/package names

    Examples:
        >>> code = '''
        ... import numpy as np
        ... from sklearn.model_selection import train_test_split
        ... import cv2
        ... '''
        >>> extract_imports(code)
        {'numpy', 'sklearn', 'cv2'}
    """
    imports = set()

    # Pattern 1: import module
    # Examples: import numpy, import numpy as np
    pattern1 = r'^import\s+([a-zA-Z0-9_\.]+)'
    matches = re.findall(pattern1, code, re.MULTILINE)
    for match in matches:
        # Get the top-level module (e.g., 'sklearn' from 'sklearn.model_selection')
        base_module = match.split('.')[0]
        imports.add(base_module)

    # Pattern 2: from module import ...
    # Examples: from sklearn.model_selection import train_test_split
    pattern2 = r'^from\s+([a-zA-Z0-9_\.]+)\s+import'
    matches = re.findall(pattern2, code, re.MULTILINE)
    for match in matches:
        # Get the top-level module
        base_module = match.split('.')[0]
        imports.add(base_module)

    # Pattern 3: import multiple modules
    # Examples: import os, sys, json
    pattern3 = r'^import\s+([a-zA-Z0-9_,\s\.]+)'
    matches = re.findall(pattern3, code, re.MULTILINE)
    for match in matches:
        # Split by comma and process each
        modules = match.split(',')
        for module in modules:
            # Remove 'as alias' part if present
            module = module.split(' as ')[0].strip()
            base_module = module.split('.')[0]
            if base_module:
                imports.add(base_module)

    return imports


def map_import_to_package(import_name: str) -> str:
    """
    Map an import name to its corresponding PyPI/conda package name.

    Args:
        import_name: Name used in import statement

    Returns:
        Corresponding package name

    Examples:
        >>> map_import_to_package('cv2')
        'opencv-python'
        >>> map_import_to_package('sklearn')
        'scikit-learn'
        >>> map_import_to_package('numpy')
        'numpy'
    """
    return IMPORT_TO_PACKAGE.get(import_name, import_name)
