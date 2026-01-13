"""
System Checker - Pre-flight system validation.
No LLM calls, just pure Python checks.
"""

import logging
import shutil
import subprocess
import platform
from typing import Tuple, List

logger = logging.getLogger(__name__)


class SystemChecker:
    """Performs system pre-flight checks before starting analysis."""

    def __init__(self):
        self.os_type = platform.system()
        self.chip_info = self._get_detailed_chip_info()

    def _get_detailed_chip_info(self) -> str:
        """Detect specific chip model (e.g., Apple M4)."""
        if self.os_type == "Darwin":
            try:
                # macOS specific command to get CPU brand
                command = ["sysctl", "-n", "machdep.cpu.brand_string"]
                chip = subprocess.check_output(command).decode().strip()
                return f"macOS ({platform.machine()}) - {chip}"
            except Exception:
                return f"macOS ({platform.machine()})"
        elif self.os_type == "Linux":
             return f"Linux ({platform.machine()})"
        else:
            return f"{self.os_type} ({platform.machine()})"

    def check_conda_installed(self) -> Tuple[bool, str]:
        """
        Check if conda is installed and accessible.
        """
        try:
            if not (shutil.which("conda") or shutil.which("mamba")):
                return False, "Conda is not installed or not in PATH."

            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Conda installed: {version}"
            else:
                return False, "Conda command failed to execute."

        except subprocess.TimeoutExpired:
            return False, "Conda command timed out."
        except Exception as e:
            logger.error(f"Error checking conda: {e}")
            return False, f"Error checking conda: {str(e)}"

    def check_disk_space(self, required_gb: float = 5.0) -> Tuple[bool, str]:
        """Check if enough disk space available."""
        try:
            stat = shutil.disk_usage(".")
            free_gb = stat.free / (1024 ** 3)

            if free_gb >= required_gb:
                return True, f"Disk space: {free_gb:.1f} GB available"
            else:
                return False, f"Insufficient disk space: {free_gb:.1f} GB available"
        except Exception:
            return True, "Disk space check skipped"

    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version is compatible."""
        import sys
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        if version.major >= 3 and version.minor >= 7:
            return True, f"Python {version_str}"
        else:
            return False, f"Python {version_str} is too old. Python 3.7+ required."

    def run_all_checks(self) -> Tuple[bool, List[str], str]:
        """
        Run all system checks before starting.
        Returns: (all_passed, messages, system_info_string)
        """
        messages = []
        all_passed = True

        # 1. System Context Detection
        messages.append(f"💻 System Detected: {self.chip_info}")
        if "Apple" in self.chip_info and "M" in self.chip_info:
             messages.append("   👉 Apple Silicon detected. Will prioritize 'conda-forge'.")

        # 2. Python Check
        success, msg = self.check_python_version()
        messages.append(("✓" if success else "✗") + f" {msg}")
        if not success: all_passed = False

        # 3. Conda Check
        success, msg = self.check_conda_installed()
        messages.append(("✓" if success else "✗") + f" {msg}")
        if not success: all_passed = False

        # 4. Disk Check
        success, msg = self.check_disk_space()
        messages.append(("✓" if success else "⚠") + f" {msg}")

        return all_passed, messages, self.chip_info