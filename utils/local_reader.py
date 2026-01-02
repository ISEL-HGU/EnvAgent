"""
Local file reader for analyzing project directories.
Reads various project files to gather dependency information.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Set

from .helpers import extract_imports, map_import_to_package

logger = logging.getLogger(__name__)


class LocalReader:
    """Reads local project files for analysis."""

    # Files to read if they exist
    TARGET_FILES = [
        "README.md",
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
    ]

    # Directories to exclude when searching for Python files
    EXCLUDE_DIRS = {
        # Python/Build artifacts
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".nox",
        ".mypy_cache",
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
        "*.egg",
        "wheels",
        "sdist",

        # Virtual environments
        "venv",
        ".venv",
        "env",
        "ENV",
        "virtualenv",

        # Version control
        ".git",
        ".github",
        ".gitlab",
        ".circleci",
        ".svn",
        ".hg",

        # IDEs
        ".idea",
        ".vscode",
        ".settings",
        ".project",
        ".pydevproject",

        # Testing
        "tests",
        "test",
        "testing",
        "coverage",
        ".coverage",
        "htmlcov",

        # Documentation
        "docs",
        "doc",
        "documentation",

        # Examples/Samples
        "examples",
        "example",
        "samples",
        "sample",
        "demo",
        "demos",

        # Benchmarks
        "benchmarks",
        "benchmark",

        # Scripts/Tools
        "scripts",
        "tools",

        # Assets
        "assets",
        "images",
        "static",
        "media",
        "public",

        # Data
        "data",
        "datasets",
        "checkpoints",
        "weights",
        "models",

        # Logs/Temp
        "logs",
        "log",
        "tmp",
        "temp",
        "cache",

        # Migrations/Locale
        "migrations",
        "locale",
        "locales",
        "i18n",
        "l10n",

        # Dependencies
        "node_modules",
        "vendor",
        "third_party",
        "external",
        "lib",
        "libs",

        # Output
        "output",
        "out",
        "results",
    }

    def __init__(self, directory_path: str):
        """
        Initialize the LocalReader.

        Args:
            directory_path: Path to the project directory to analyze

        Raises:
            ValueError: If the directory doesn't exist
        """
        self.directory_path = Path(directory_path).resolve()

        if not self.directory_path.exists():
            raise ValueError(f"Directory does not exist: {self.directory_path}")

        if not self.directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.directory_path}")

        logger.info(f"Initialized LocalReader for: {self.directory_path}")

    def read_files(self) -> Dict[str, str]:
        """
        Read all relevant files from the project directory.

        Returns:
            Dictionary with filename as key and file content as value.
            Includes a special key '__extracted_imports__' with all discovered imports.
        """
        files_content = {}
        all_imports: Set[str] = set()

        # Read target files
        for filename in self.TARGET_FILES:
            file_path = self.directory_path / filename
            if file_path.exists() and file_path.is_file():
                try:
                    content = self._read_file(file_path)
                    if content:
                        files_content[filename] = content
                        logger.info(f"Read file: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to read {filename}: {e}")

        # Read all Python files and extract imports
        python_files = self._find_python_files()
        for py_file in python_files:
            try:
                content = self._read_file(py_file)
                if content:
                    # Use relative path as key
                    relative_path = py_file.relative_to(self.directory_path)
                    files_content[str(relative_path)] = content
                    logger.info(f"Read Python file: {relative_path}")

                    # Extract imports from this file
                    imports = extract_imports(content)
                    all_imports.update(imports)
            except Exception as e:
                logger.warning(f"Failed to read {py_file}: {e}")

        # Create import summary
        if all_imports:
            # Map import names to package names
            packages = set()
            for imp in all_imports:
                # Filter out standard library imports
                if not self._is_stdlib(imp):
                    pkg = map_import_to_package(imp)
                    packages.add(pkg)

            # Add summary to files_content
            import_summary = "# Extracted Imports from Python Files\n\n"
            import_summary += "## Import Names Found:\n"
            import_summary += ", ".join(sorted(all_imports))
            import_summary += "\n\n## Mapped to Package Names:\n"
            import_summary += ", ".join(sorted(packages))

            files_content["__extracted_imports__"] = import_summary
            logger.info(f"Extracted {len(all_imports)} unique imports, mapped to {len(packages)} packages")

        logger.info(f"Total files read: {len(files_content)}")
        return files_content

    def _is_stdlib(self, module_name: str) -> bool:
        """
        Check if a module is part of the Python standard library.

        Args:
            module_name: Name of the module to check

        Returns:
            True if module is in standard library, False otherwise
        """
        # Common standard library modules
        stdlib_modules = {
            'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'binascii',
            'builtins', 'calendar', 'collections', 'copy', 'csv', 'datetime',
            'decimal', 'email', 'enum', 'functools', 'glob', 'gzip', 'hashlib',
            'heapq', 'html', 'http', 'io', 'itertools', 'json', 'logging',
            'math', 'multiprocessing', 'operator', 'os', 'pathlib', 'pickle',
            'platform', 'queue', 'random', 're', 'shutil', 'signal', 'socket',
            'sqlite3', 'ssl', 'statistics', 'string', 'struct', 'subprocess',
            'sys', 'tempfile', 'textwrap', 'threading', 'time', 'traceback',
            'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref',
            'xml', 'zipfile', 'zlib'
        }
        return module_name in stdlib_modules

    def _read_file(self, file_path: Path) -> str:
        """
        Read content from a file.

        Args:
            file_path: Path to the file to read

        Returns:
            File content as string
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with a different encoding if UTF-8 fails
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to decode {file_path}: {e}")
                return ""

    def _find_python_files(self) -> list[Path]:
        """
        Find all Python files in the directory, excluding certain directories.

        Returns:
            List of paths to Python files
        """
        python_files = []

        for root, dirs, files in os.walk(self.directory_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            # Add Python files
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        return python_files
