"""
File Filter - Rule-based file filtering.
No LLM calls, just pure Python logic to filter relevant files.
"""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class FileFilter:
    """Filters files to find only those relevant for dependency analysis."""

    # Directories to exclude from scanning
    EXCLUDE_DIRS = {
        '__pycache__', '.git', '.github', 'venv', 'env', '.venv',
        'node_modules', '.idea', '.vscode', 'dist', 'build',
        'egg-info', '.eggs', '.tox', '.pytest_cache', '.mypy_cache',
        'docs', 'documentation', 'examples', 'tests', 'test',
        'assets', 'images', 'static', 'templates', 'migrations',
        '.DS_Store', 'htmlcov', 'coverage', '.coverage',
        'wheels', 'sdist', 'var', 'instance'
    }

    # File patterns to exclude
    EXCLUDE_FILE_PATTERNS = {
        '.gitignore', '.dockerignore', 'LICENSE', 'CHANGELOG.md',
        'CONTRIBUTING.md', 'Makefile', '.pylintrc', '.flake8',
        '.editorconfig', '.pre-commit-config.yaml', 'tox.ini',
        'pytest.ini', '.coveragerc', 'mypy.ini'
    }

    # File extensions to exclude
    EXCLUDE_EXTENSIONS = {
        '.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.toml',
        '.cfg', '.ini', '.sh', '.bat', '.cmd', '.ps1',
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.db', '.sqlite', '.sqlite3', '.log'
    }

    # Only include these extensions for dependency analysis
    INCLUDE_EXTENSIONS = {'.py'}

    # Special files to always include (dependency-related)
    ALWAYS_INCLUDE = {
        'requirements.txt', 'requirements-dev.txt', 'requirements-test.txt',
        'setup.py', 'setup.cfg', 'pyproject.toml',
        'environment.yml', 'environment.yaml', 'conda.yaml',
        'Pipfile', 'Pipfile.lock', 'poetry.lock'
    }

    def __init__(self, max_file_size_kb: int = 500):
        """
        Initialize FileFilter.

        Args:
            max_file_size_kb: Maximum file size to process in KB
        """
        self.max_file_size_bytes = max_file_size_kb * 1024

    def _should_exclude_dir(self, dir_path: Path) -> bool:
        """
        Check if directory should be excluded.

        Args:
            dir_path: Directory path to check

        Returns:
            True if should exclude, False otherwise
        """
        dir_name = dir_path.name.lower()

        # Check against exclude list
        if dir_name in self.EXCLUDE_DIRS:
            return True

        # Exclude hidden directories (except .github for workflows)
        if dir_name.startswith('.') and dir_name not in {'.github'}:
            return True

        return False

    def _should_include_file(self, file_path: Path) -> bool:
        """
        Check if file should be included for analysis.

        Args:
            file_path: File path to check

        Returns:
            True if should include, False otherwise
        """
        file_name = file_path.name
        file_ext = file_path.suffix.lower()

        # Always include special dependency files
        if file_name in self.ALWAYS_INCLUDE:
            logger.debug(f"Including special file: {file_name}")
            return True

        # Exclude by file pattern
        if file_name in self.EXCLUDE_FILE_PATTERNS:
            return False

        # Exclude by extension
        if file_ext in self.EXCLUDE_EXTENSIONS:
            return False

        # Include only specific extensions
        if file_ext not in self.INCLUDE_EXTENSIONS:
            return False

        # Check file size
        try:
            if file_path.stat().st_size > self.max_file_size_bytes:
                logger.warning(f"Skipping large file: {file_name} ({file_path.stat().st_size / 1024:.0f} KB)")
                return False
        except Exception as e:
            logger.warning(f"Could not check size of {file_name}: {e}")
            return False

        return True

    def get_relevant_files(self, project_path: str) -> List[Path]:
        """
        Get all relevant files for dependency analysis.

        Args:
            project_path: Root directory of the project

        Returns:
            List of Path objects for relevant files
        """
        project_dir = Path(project_path).resolve()

        if not project_dir.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return []

        if not project_dir.is_dir():
            logger.error(f"Project path is not a directory: {project_path}")
            return []

        relevant_files = []

        # Walk through directory tree
        for item in project_dir.rglob("*"):
            try:
                # Skip if it's a directory
                if item.is_dir():
                    continue

                # Check if file is in an excluded directory
                is_in_excluded_dir = any(
                    self._should_exclude_dir(parent)
                    for parent in item.parents
                    if parent != project_dir
                )

                if is_in_excluded_dir:
                    continue

                # Check if file should be included
                if self._should_include_file(item):
                    relevant_files.append(item)

            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access {item}: {e}")
                continue

        # Sort by file type priority: dependency files first, then .py files
        def sort_key(path: Path) -> tuple:
            # Priority 0: dependency definition files
            if path.name in self.ALWAYS_INCLUDE:
                return (0, path.name)
            # Priority 1: Python files
            elif path.suffix == '.py':
                return (1, str(path))
            # Priority 2: others
            else:
                return (2, str(path))

        relevant_files.sort(key=sort_key)

        logger.info(f"Found {len(relevant_files)} relevant files in {project_path}")
        return relevant_files

    def get_dependency_files(self, project_path: str) -> List[Path]:
        """
        Get only dependency definition files.

        Args:
            project_path: Root directory of the project

        Returns:
            List of Path objects for dependency files
        """
        all_files = self.get_relevant_files(project_path)
        return [f for f in all_files if f.name in self.ALWAYS_INCLUDE]

    def get_python_files(self, project_path: str) -> List[Path]:
        """
        Get only Python source files.

        Args:
            project_path: Root directory of the project

        Returns:
            List of Path objects for .py files
        """
        all_files = self.get_relevant_files(project_path)
        return [f for f in all_files if f.suffix == '.py']
