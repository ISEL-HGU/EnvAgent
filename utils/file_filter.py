"""
File Filter Module
Responsible for selecting relevant files for dependency analysis while
excluding system files, binary data, and heavy directories (like node_modules)
to optimize processing speed and token usage.
"""

import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class FileFilter:
    """
    Filters files to find only those relevant for dependency analysis.
    Implements 'Early Pruning' to skip unnecessary directory traversal.
    """

    # Directories to completely ignore during traversal
    # This prevents entering heavy folders like node_modules or .git
    EXCLUDE_DIRS = {
        '__pycache__', '.git', '.github', 'venv', 'env', '.venv',
        'node_modules', '.idea', '.vscode', 'dist', 'build',
        'egg-info', '.eggs', '.tox', '.pytest_cache', '.mypy_cache',
        'docs', 'documentation', 'examples', 'tests', 'test',
        'assets', 'images', 'static', 'templates', 'migrations',
        '.DS_Store', 'htmlcov', 'coverage', '.coverage',
        'wheels', 'sdist', 'var', 'instance', 'public', 'lib',
        'site-packages'
    }

    # Specific filenames to ignore (configs, linters, etc.)
    EXCLUDE_FILE_PATTERNS = {
        '.gitignore', '.dockerignore', 'LICENSE', 'CHANGELOG.md',
        'CONTRIBUTING.md', 'Makefile', '.pylintrc', '.flake8',
        '.editorconfig', '.pre-commit-config.yaml', 'tox.ini',
        'pytest.ini', '.coveragerc', 'mypy.ini', 'Procfile'
    }

    # File extensions to ignore (binaries, data, logs, media)
    EXCLUDE_EXTENSIONS = {
        '.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.toml',
        '.cfg', '.ini', '.sh', '.bat', '.cmd', '.ps1',
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
        '.db', '.sqlite', '.sqlite3', '.log', '.css', '.js', '.html',
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin'
    }

    # Extensions to analyze for source code
    # Included .ipynb for Jupyter Notebook support
    INCLUDE_EXTENSIONS = {'.py', '.ipynb'}

    # High-priority dependency definition files
    # These are always included regardless of other rules
    ALWAYS_INCLUDE = {
        'requirements.txt', 'requirements-dev.txt', 'requirements-test.txt',
        'setup.py', 'setup.cfg', 'pyproject.toml',
        'environment.yml', 'environment.yaml', 'conda.yaml',
        'Pipfile', 'Pipfile.lock', 'poetry.lock', 'Dockerfile'
    }

    def __init__(self, max_file_size_kb: int = 500):
        """
        Initialize the file filter.

        Args:
            max_file_size_kb: Files larger than this (in KB) will be skipped 
                              to avoid token limits or performance issues.
        """
        self.max_file_size_bytes = max_file_size_kb * 1024

    def _should_exclude_dir_name(self, dir_name: str) -> bool:
        """
        Check if a directory name is in the blocklist.
        """
        if dir_name in self.EXCLUDE_DIRS:
            return True
        # Exclude hidden directories (start with .) but allow .github workflows
        if dir_name.startswith('.') and dir_name not in {'.github'}:
            return True
        return False

    def _should_include_file(self, file_path: Path) -> bool:
        """
        Determine if a specific file should be included in analysis.
        """
        file_name = file_path.name
        file_ext = file_path.suffix.lower()

        # 1. Always include priority configuration files
        if file_name in self.ALWAYS_INCLUDE:
            return True

        # 2. Check exclusion patterns
        if file_name in self.EXCLUDE_FILE_PATTERNS:
            return False
        if file_ext in self.EXCLUDE_EXTENSIONS:
            return False

        # 3. Check inclusion extensions (Source Code)
        if file_ext not in self.INCLUDE_EXTENSIONS:
            return False

        # 4. Check file size (Skip overly large files)
        try:
            if file_path.stat().st_size > self.max_file_size_bytes:
                logger.debug(f"Skipping large file: {file_name}")
                return False
        except OSError:
            # Handle cases where file access fails (e.g., broken symlinks)
            return False

        return True

    def get_relevant_files(self, project_path: str) -> List[Path]:
        """
        Scan the project directory and return a list of relevant files.
        Uses os.walk with in-place list modification for 'Early Pruning'.

        Args:
            project_path: The root directory to scan.

        Returns:
            List[Path]: A sorted list of relevant file paths.
        """
        project_dir = Path(project_path).resolve()
        relevant_files = []

        if not project_dir.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return []

        # Walk the directory tree
        for root, dirs, files in os.walk(str(project_dir)):
            # [Early Pruning Optimization]
            # Modify 'dirs' list in-place to prevent os.walk from entering excluded directories.
            # This significantly speeds up scanning by skipping node_modules, .git, etc.
            dirs[:] = [d for d in dirs if not self._should_exclude_dir_name(d)]

            for file in files:
                file_path = Path(root) / file
                
                try:
                    if self._should_include_file(file_path):
                        relevant_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Error checking file {file}: {e}")
                    continue

        # Sort files to prioritize dependency definitions
        # Order: 
        # 0. Dependency Files (requirements.txt, setup.py)
        # 1. Python Source Files (.py, .ipynb)
        # 2. Others
        def sort_key(path: Path) -> tuple:
            if path.name in self.ALWAYS_INCLUDE:
                return (0, path.name)
            elif path.suffix == '.py':
                return (1, str(path))
            else:
                return (2, str(path))

        relevant_files.sort(key=sort_key)

        logger.info(f"FileFilter: Found {len(relevant_files)} relevant files in {project_path}")
        return relevant_files

    def get_dependency_files(self, project_path: str) -> List[Path]:
        """
        Helper to retrieve only dependency definition files.
        """
        all_files = self.get_relevant_files(project_path)
        return [f for f in all_files if f.name in self.ALWAYS_INCLUDE]