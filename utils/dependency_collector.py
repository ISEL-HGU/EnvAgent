"""
Dependency Collector - Extracts dependencies from files one by one.
Avoids token limits by processing files individually without LLM.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Set, List

logger = logging.getLogger(__name__)


class DependencyCollector:
    """Extracts imports from Python files and collects dependency information."""

    # Common import name -> package name mapping
    IMPORT_MAP = {
        'cv2': 'opencv-python',
        'PIL': 'pillow',
        'sklearn': 'scikit-learn',
        'skimage': 'scikit-image',
        'yaml': 'pyyaml',
        'bs4': 'beautifulsoup4',
        'dotenv': 'python-dotenv',
        'git': 'gitpython',
        'serial': 'pyserial',
        'usb': 'pyusb',
        'jwt': 'pyjwt',
        'magic': 'python-magic',
        'dateutil': 'python-dateutil',
        'Crypto': 'pycryptodome',
        'OpenSSL': 'pyopenssl',
        'bottle': 'bottle',
        'flask': 'flask',
        'django': 'django',
        'fastapi': 'fastapi',
        'starlette': 'starlette',
        'aiohttp': 'aiohttp',
        'requests': 'requests',
        'httpx': 'httpx',
        'tornado': 'tornado',
        'sqlalchemy': 'sqlalchemy',
        'psycopg2': 'psycopg2-binary',
        'pymongo': 'pymongo',
        'redis': 'redis',
        'celery': 'celery',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scipy': 'scipy',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'plotly': 'plotly',
        'torch': 'torch',
        'tensorflow': 'tensorflow',
        'keras': 'keras',
        'transformers': 'transformers',
        'datasets': 'datasets',
        'tokenizers': 'tokenizers',
        'accelerate': 'accelerate',
        'diffusers': 'diffusers',
        'openai': 'openai',
        'anthropic': 'anthropic',
        'langchain': 'langchain',
        'llama_index': 'llama-index',
    }

    # Standard library modules to ignore (Python 3.7+)
    STDLIB = {
        # Core
        'os', 'sys', 're', 'json', 'time', 'datetime', 'collections',
        'itertools', 'functools', 'pathlib', 'typing', 'abc', 'copy',
        'math', 'random', 'string', 'io', 'tempfile', 'shutil', 'glob',
        'subprocess', 'threading', 'multiprocessing', 'concurrent',
        'asyncio', 'socket', 'http', 'urllib', 'email', 'html', 'xml',

        # Error/Debug
        'logging', 'warnings', 'traceback', 'inspect', 'types',
        'dataclasses', 'enum', 'contextlib', 'pickle', 'hashlib',

        # Data
        'base64', 'struct', 'codecs', 'csv', 'configparser', 'argparse',

        # Testing
        'unittest', 'doctest', 'pdb', 'profile', 'timeit', 'dis',

        # Memory/Performance
        'gc', 'weakref', 'operator', 'statistics', 'decimal', 'fractions',
        'numbers', 'cmath', 'array', 'bisect', 'heapq', 'queue',

        # Text
        'textwrap', 'difflib', 'secrets', 'uuid', 'platform', 'ctypes',

        # Import/Package
        'importlib', 'pkgutil', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',

        # Database
        'sqlite3',

        # Compression/Encoding
        'zlib', 'binascii', 'pprint', 'reprlib', 'locale',

        # I18n
        'gettext', 'calendar', 'atexit', 'signal', 'mmap', 'select',

        # System
        'selectors', 'errno', 'faulthandler', 'resource', 'sysconfig',
        'site', 'code', 'codeop', 'distutils', 'ensurepip', 'venv',

        # Dev Tools
        'lib2to3', 'test', 'pydoc', 'turtle', 'cmd', 'shlex', 'getopt',

        # Network
        'getpass', 'telnetlib', 'imaplib', 'poplib', 'smtplib', 'ftplib',
        'netrc', 'cgi', 'cgitb', 'wsgiref', 'xmlrpc', 'ipaddress',

        # Media
        'audioop', 'wave', 'colorsys',

        # Terminal
        'curses', 'readline', 'rlcompleter',

        # Internal
        '_thread', 'builtins', 'runpy', 'symtable', 'token', 'keyword',
        'tokenize', 'tabnanny', 'py_compile', 'compileall', 'parser',

        # File
        'fileinput', 'linecache', 'fnmatch', 'stat', 'filecmp',
        'posixpath', 'ntpath', 'genericpath', 'macpath', 'posix', 'nt',

        # POSIX
        'pwd', 'grp', 'termios', 'tty', 'pty', 'fcntl', 'pipes', 'ossaudiodev',
    }

    def __init__(self, output_file: str = "dependency_summary.txt"):
        """
        Initialize DependencyCollector.

        Args:
            output_file: Path where summary will be saved
        """
        self.output_file = output_file
        self.all_imports = set()
        self.cuda_detected = False
        self.python_hints = []
        self.file_count = 0
        self.version_requirements = {}  # package -> version from requirements.txt

    def extract_imports_from_file(self, filepath: str, content: str) -> Set[str]:
        """
        Extract import statements from a single Python file.

        Args:
            filepath: Path to the file (for logging)
            content: File content

        Returns:
            Set of top-level package names
        """
        imports = set()

        # Match: import xxx / from xxx import yyy
        import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments
            if line.startswith('#'):
                continue

            match = re.match(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2)
                # Get top-level package
                top_level = module.split('.')[0]

                # Skip stdlib and relative imports
                if top_level not in self.STDLIB and not top_level.startswith('.'):
                    imports.add(top_level)

        return imports

    def detect_cuda_usage(self, content: str) -> bool:
        """
        Detect CUDA/GPU usage in code.

        Args:
            content: File content

        Returns:
            True if CUDA usage detected
        """
        cuda_patterns = [
            'torch.cuda',
            '.cuda()',
            'device="cuda"',
            "device='cuda'",
            'tf.config.list_physical_devices',
            'tensorflow.*GPU',
            'CUDAExecutionProvider',
        ]

        for pattern in cuda_patterns:
            if re.search(pattern, content):
                return True

        return False

    def detect_python_version_hints(self, content: str) -> List[str]:
        """
        Detect Python version hints from code patterns.

        Args:
            content: File content

        Returns:
            List of minimum Python versions detected
        """
        hints = []

        # match/case = 3.10+
        if re.search(r'\bmatch\b.*:', content) and re.search(r'\bcase\b.*:', content):
            hints.append('3.10')

        # from typing import Literal = 3.8+
        if 'from typing import' in content and 'Literal' in content:
            hints.append('3.8')

        # Walrus operator := = 3.8+
        if ':=' in content:
            hints.append('3.8')

        # f-strings with = for debug = 3.8+
        if re.search(r'f["\'].*\{.*=.*\}', content):
            hints.append('3.8')

        # Positional-only parameters / = 3.8+
        if re.search(r'def\s+\w+\([^)]*,\s*/\s*[,)]', content):
            hints.append('3.8')

        return hints

    def parse_requirements_file(self, content: str):
        """
        Parse requirements.txt for version constraints.

        Args:
            content: Content of requirements.txt
        """
        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#') or line.startswith('-'):
                continue

            # Parse: package==version, package>=version, etc.
            match = re.match(r'([a-zA-Z0-9_-]+)\s*(==|>=|<=|>|<|~=)\s*([0-9.]+)', line)
            if match:
                package, operator, version = match.groups()
                self.version_requirements[package.lower()] = f"{operator}{version}"
                logger.debug(f"Found version requirement: {package}{operator}{version}")

    def process_file(self, filepath: str, content: str):
        """
        Process a single file and accumulate dependency information.

        Args:
            filepath: Path to the file
            content: File content
        """
        self.file_count += 1

        # Handle requirements.txt
        if filepath.endswith('requirements.txt'):
            self.parse_requirements_file(content)
            return

        # Handle Python files
        if filepath.endswith('.py'):
            # Extract imports
            imports = self.extract_imports_from_file(filepath, content)
            self.all_imports.update(imports)

            # Detect CUDA
            if self.detect_cuda_usage(content):
                self.cuda_detected = True

            # Detect Python version hints
            hints = self.detect_python_version_hints(content)
            self.python_hints.extend(hints)

            logger.debug(f"Processed {filepath}: {len(imports)} imports")

    def map_import_to_package(self, import_name: str) -> str:
        """
        Map import name to pip/conda package name.

        Args:
            import_name: Import name from code

        Returns:
            Corresponding package name
        """
        return self.IMPORT_MAP.get(import_name, import_name)

    def get_summary(self) -> Dict:
        """
        Get collected dependency summary as dictionary.

        Returns:
            Dictionary with python_version, cuda_required, packages, etc.
        """
        # Map imports to package names
        packages = sorted([self.map_import_to_package(imp) for imp in self.all_imports])

        # Determine Python version
        if self.python_hints:
            # Get maximum version requirement
            python_version = max(self.python_hints)
        else:
            python_version = "3.9"

        return {
            "python_version": python_version,
            "cuda_required": self.cuda_detected,
            "packages": packages,
            "package_count": len(packages),
            "files_processed": self.file_count,
            "version_requirements": self.version_requirements,
        }

    def save_summary(self) -> str:
        """
        Save collected dependencies to summary file.

        Returns:
            Path to saved summary file
        """
        summary = self.get_summary()

        content = f"""# Dependency Summary
# Auto-generated by EnvAgent v2

## Files Processed
{summary['files_processed']}

## Python Version
{summary['python_version']}

## CUDA Required
{summary['cuda_required']}

## Packages Found ({summary['package_count']})
"""

        # Add packages with version requirements if available
        for package in summary['packages']:
            pkg_lower = package.lower()
            if pkg_lower in summary['version_requirements']:
                content += f"{package}{summary['version_requirements'][pkg_lower]}\n"
            else:
                content += f"{package}\n"

        content += """
## Notes
- Extracted from source code imports
- Standard library excluded
- Import names mapped to package names
- Version requirements from requirements.txt (if available)
"""

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Dependency summary saved to {self.output_file}")
        return self.output_file
