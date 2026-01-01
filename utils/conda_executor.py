"""
Conda executor for creating and managing conda environments.
"""

import logging
import subprocess
from pathlib import Path
from typing import Tuple

from .helpers import sanitize_env_name

logger = logging.getLogger(__name__)


class CondaExecutor:
    """Executes conda commands for environment management."""

    def __init__(self):
        """Initialize the CondaExecutor."""
        logger.info("CondaExecutor initialized")

    def create_environment(self, yml_path: str, env_name: str) -> Tuple[bool, str]:
        """
        Create a conda environment from a YAML file.

        Args:
            yml_path: Path to the environment.yml file
            env_name: Name of the environment to create

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Sanitize environment name to ensure it's valid for conda
        sanitized_name = sanitize_env_name(env_name)
        if sanitized_name != env_name:
            logger.info(f"Sanitized environment name: '{env_name}' -> '{sanitized_name}'")

        yml_file = Path(yml_path)

        if not yml_file.exists():
            error_msg = f"Environment file not found: {yml_path}"
            logger.error(error_msg)
            return False, error_msg

        logger.info(f"Creating conda environment '{sanitized_name}' from {yml_path}")

        try:
            # Run conda env create command with sanitized name
            result = subprocess.run(
                ["conda", "env", "create", "-f", str(yml_file), "-n", sanitized_name, "--yes"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"Successfully created environment '{sanitized_name}'")
                return True, ""
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                logger.error(f"Failed to create environment: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "Conda command timed out after 10 minutes"
            logger.error(error_msg)
            return False, error_msg

        except FileNotFoundError:
            error_msg = "Conda command not found. Make sure conda is installed and in PATH"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error during conda environment creation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def remove_environment(self, env_name: str) -> Tuple[bool, str]:
        """
        Remove a conda environment.

        Args:
            env_name: Name of the environment to remove

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Sanitize environment name
        sanitized_name = sanitize_env_name(env_name)
        if sanitized_name != env_name:
            logger.info(f"Sanitized environment name: '{env_name}' -> '{sanitized_name}'")

        logger.info(f"Removing conda environment '{sanitized_name}'")

        try:
            result = subprocess.run(
                ["conda", "env", "remove", "-n", sanitized_name, "--yes"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info(f"Successfully removed environment '{sanitized_name}'")
                return True, ""
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                # Don't treat "environment doesn't exist" as an error
                if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                    logger.info(f"Environment '{sanitized_name}' does not exist (already removed)")
                    return True, ""
                logger.warning(f"Failed to remove environment: {error_msg}")
                return False, error_msg

        except FileNotFoundError:
            error_msg = "Conda command not found"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error during environment removal: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def environment_exists(self, env_name: str) -> bool:
        """
        Check if a conda environment exists.

        Args:
            env_name: Name of the environment to check

        Returns:
            True if environment exists, False otherwise
        """
        # Sanitize environment name
        sanitized_name = sanitize_env_name(env_name)

        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Check if sanitized_name appears in the output
                return sanitized_name in result.stdout
            return False

        except Exception as e:
            logger.warning(f"Failed to check environment existence: {e}")
            return False
