"""
System Checker - Pre-flight system validation.
No LLM calls, just pure Python checks.
"""

import logging
import shutil
import subprocess
from typing import Tuple, List

logger = logging.getLogger(__name__)


class SystemChecker:
    """Performs system pre-flight checks before starting analysis."""

    def check_conda_installed(self) -> Tuple[bool, str]:
        """
        Check if conda is installed and accessible.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if conda command exists
            if not shutil.which("conda"):
                return False, "Conda is not installed or not in PATH. Please install Conda first."

            # Try to get conda version
            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"Conda detected: {version}")
                return True, f"Conda installed: {version}"
            else:
                return False, "Conda command failed to execute."

        except subprocess.TimeoutExpired:
            return False, "Conda command timed out."
        except Exception as e:
            logger.error(f"Error checking conda: {e}")
            return False, f"Error checking conda: {str(e)}"

    def check_disk_space(self, required_gb: float = 5.0) -> Tuple[bool, str]:
        """
        Check if enough disk space available.

        Args:
            required_gb: Minimum required disk space in GB

        Returns:
            Tuple of (success, message)
        """
        try:
            import shutil
            stat = shutil.disk_usage(".")
            free_gb = stat.free / (1024 ** 3)

            if free_gb >= required_gb:
                return True, f"Disk space: {free_gb:.1f} GB available"
            else:
                return False, f"Insufficient disk space: {free_gb:.1f} GB available, {required_gb} GB required"

        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            # Don't fail on disk space check errors
            return True, "Disk space check skipped"

    def check_python_version(self) -> Tuple[bool, str]:
        """
        Check if Python version is compatible.

        Returns:
            Tuple of (success, message)
        """
        import sys

        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        # Require Python 3.7+
        if version.major >= 3 and version.minor >= 7:
            return True, f"Python {version_str}"
        else:
            return False, f"Python {version_str} is too old. Python 3.7+ required."

    def run_all_checks(self) -> Tuple[bool, List[str]]:
        """
        Run all system checks before starting.

        Returns:
            Tuple of (all_passed, list_of_messages)
        """
        messages = []
        all_passed = True

        # Check Python version
        success, msg = self.check_python_version()
        messages.append(("✓" if success else "✗") + f" {msg}")
        if not success:
            all_passed = False

        # Check conda installation (critical)
        success, msg = self.check_conda_installed()
        messages.append(("✓" if success else "✗") + f" {msg}")
        if not success:
            all_passed = False

        # Check disk space (warning only)
        success, msg = self.check_disk_space()
        messages.append(("✓" if success else "⚠") + f" {msg}")
        # Don't fail on disk space warnings

        return all_passed, messages
