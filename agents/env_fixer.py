"""
Environment Fixer Agent.
Uses OpenAI GPT-4 to fix conda environment errors.
"""

import logging
import re
from openai import OpenAI

from config.settings import settings
from utils.memory import Memory

logger = logging.getLogger(__name__)


class EnvironmentFixer:
    """Fixes conda environment errors using AI."""

    FIX_PROMPT = """You are a Conda environment.yml fixer. A conda environment creation FAILED.

## CURRENT environment.yml:
{current_yml}

## CONDA ERROR:
{error_message}

## PREVIOUS FIX ATTEMPTS:
{error_history}

## YOUR TASK:
You MUST fix the error by modifying the YAML. DO NOT return it unchanged.

### Common fixes for specific errors:

**"PackagesNotFoundError" or "package not found":**
- REMOVE the package entirely if not essential
- OR change version (try removing version constraint)
- OR move to pip section instead of conda

**"cudnn" or "cudatoolkit" not found:**
- FIRST: Check if nvidia channel is in channels section - if not, add "- nvidia" as FIRST channel
- SECOND: Change cudnn from exact version (e.g., cudnn=8.6) to flexible version (cudnn>=8.0)
- THIRD: If still failing, try just "cudnn" without any version
- LAST RESORT: Remove cudnn line entirely (cudatoolkit often includes cuDNN)

**"UnsatisfiableError" or version conflict:**
- Remove specific version constraints (e.g., ==1.0.0 → no version)
- Remove one of the conflicting packages
- Downgrade package versions

**Platform-specific error:**
- Remove the package that's not available on this platform

## CRITICAL RULES:
1. You MUST make changes - do NOT return unchanged YAML
2. When in doubt, REMOVE the problematic package
3. Return ONLY the fixed YAML, no explanations
4. Do NOT use markdown code blocks (no ```)

## FIXED environment.yml (MUST BE DIFFERENT):
"""

    def __init__(self):
        """Initialize the EnvironmentFixer with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentFixer initialized")

    def fix(self, current_yml: str, error_message: str, memory: Memory) -> str:
        """
        Generate a fixed environment.yml based on the error.

        Args:
            current_yml: Current YAML content that failed
            error_message: Error message from conda
            memory: Memory object containing error history

        Returns:
            Fixed YAML content as string
        """
        logger.info("=" * 70)
        logger.info("BEFORE FIX:")
        logger.info(current_yml)
        logger.info("=" * 70)

        print("\n" + "🔍 DEBUG: CURRENT YAML BEFORE FIX:")
        print("-" * 60)
        print(current_yml)
        print("-" * 60)

        # Format error history for context
        error_history_text = "None - this is the first attempt" if not memory.error_history else ""
        if memory.error_history:
            history_lines = []
            for i, (error, fix_desc) in enumerate(memory.error_history, 1):
                history_lines.append(f"Attempt {i}:")
                history_lines.append(f"  Error: {error[:200]}...")
                history_lines.append(f"  Fix applied: {fix_desc}")
            error_history_text = "\n".join(history_lines)

        # Prepare the prompt
        prompt = self.FIX_PROMPT.format(
            current_yml=current_yml,
            error_message=error_message,
            error_history=error_history_text
        )

        try:
            logger.info("Calling GPT-4 to fix the error...")
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in fixing Conda environment errors. You MUST make changes to fix the error."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Slightly higher for more variation
            )

            fixed_yml = response.choices[0].message.content.strip()

            # Clean up any markdown code blocks if present
            if fixed_yml.startswith("```"):
                lines = fixed_yml.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                fixed_yml = "\n".join(lines).strip()

            logger.info("=" * 70)
            logger.info("AFTER FIX:")
            logger.info(fixed_yml)
            logger.info("=" * 70)

            print("\n" + "🔧 DEBUG: FIXED YAML AFTER AI:")
            print("-" * 60)
            print(fixed_yml)
            print("-" * 60)

            # VALIDATION: Check if anything actually changed
            if self._are_yamls_identical(current_yml, fixed_yml):
                logger.warning("⚠️  LLM RETURNED UNCHANGED YAML! Forcing fix...")
                print("\n⚠️  WARNING: AI didn't change the YAML! Forcing manual fix...")
                fixed_yml = self._force_remove_problematic_package(current_yml, error_message)

                print("\n🔨 DEBUG: FORCED FIX RESULT:")
                print("-" * 60)
                print(fixed_yml)
                print("-" * 60)

            return fixed_yml

        except Exception as e:
            logger.error(f"Error generating fix: {e}")
            raise

    def _are_yamls_identical(self, yml1: str, yml2: str) -> bool:
        """
        Check if two YAML contents are identical (ignoring whitespace differences).

        Args:
            yml1: First YAML content
            yml2: Second YAML content

        Returns:
            True if identical, False otherwise
        """
        # Normalize: remove extra whitespace, sort lines for comparison
        def normalize(yml):
            lines = [line.strip() for line in yml.strip().split("\n") if line.strip()]
            return "\n".join(sorted(lines))

        return normalize(yml1) == normalize(yml2)

    def _force_remove_problematic_package(self, yml: str, error: str) -> str:
        """
        Fallback: forcefully fix the problematic package in YAML.

        For cudnn errors, tries smart fixes before removal:
        1. Add nvidia channel if missing
        2. Relax cudnn version constraint
        3. Remove cudnn entirely

        Args:
            yml: Current YAML content
            error: Error message from conda

        Returns:
            Fixed YAML with problematic package fixed or removed
        """
        logger.info("Forcing fix for problematic package...")

        # Special handling for cudnn errors
        if "cudnn" in error.lower():
            logger.info("Detected cudnn error - applying smart fixes...")

            # Strategy 1: Add nvidia channel if missing
            if "nvidia" not in yml:
                logger.info("Adding nvidia channel to resolve cudnn...")
                lines = yml.split('\n')
                fixed_lines = []
                channels_found = False

                for line in lines:
                    fixed_lines.append(line)
                    if "channels:" in line and not channels_found:
                        channels_found = True
                        # Add nvidia as first channel
                        indent = len(line) - len(line.lstrip())
                        fixed_lines.append(' ' * (indent + 2) + '- nvidia')

                if channels_found:
                    logger.info("Added nvidia channel")
                    return '\n'.join(fixed_lines)

            # Strategy 2: Relax cudnn version constraint
            lines = yml.split('\n')
            fixed_lines = []
            cudnn_fixed = False

            for line in lines:
                if 'cudnn' in line.lower() and line.strip().startswith('-'):
                    # Change exact version to flexible version
                    if '=' in line and not '>=' in line:
                        logger.info(f"Relaxing cudnn version constraint from: {line.strip()}")
                        # Replace cudnn=X.Y with cudnn>=8.0
                        fixed_line = re.sub(r'cudnn\s*=\s*[\d.]+', 'cudnn>=8.0', line)
                        fixed_lines.append(fixed_line)
                        cudnn_fixed = True
                        logger.info(f"Changed to: {fixed_line.strip()}")
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            if cudnn_fixed:
                return '\n'.join(fixed_lines)

            # Strategy 3: Remove cudnn version entirely (just "- cudnn")
            lines = yml.split('\n')
            fixed_lines = []
            cudnn_simplified = False

            for line in lines:
                if 'cudnn' in line.lower() and line.strip().startswith('-'):
                    if '=' in line or '>' in line or '<' in line:
                        indent = len(line) - len(line.lstrip())
                        fixed_line = ' ' * indent + '- cudnn'
                        fixed_lines.append(fixed_line)
                        cudnn_simplified = True
                        logger.info(f"Simplified cudnn: {line.strip()} → {fixed_line.strip()}")
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            if cudnn_simplified:
                return '\n'.join(fixed_lines)

            # Strategy 4: Last resort - remove cudnn
            logger.info("Last resort: removing cudnn entirely")

        # Extract package name from error message
        # Common patterns: "cudnn", "cudatoolkit=11.8", "package-name==1.0.0"
        problem_packages = []

        # Look for package names in error message
        if "cudnn" in error.lower():
            problem_packages.append("cudnn")
        if "cudatoolkit" in error.lower():
            problem_packages.append("cudatoolkit")

        # Try to find package names in quotes or after "PackagesNotFoundError:"
        matches = re.findall(r'["\']([a-zA-Z0-9_-]+(?:==|>=|<=)?[0-9.]*)["\']', error)
        if matches:
            for match in matches:
                pkg_name = match.split('=')[0].split('>')[0].split('<')[0]
                if pkg_name not in problem_packages:
                    problem_packages.append(pkg_name)

        # Also look for "- packagename" pattern in error
        matches = re.findall(r'- ([a-zA-Z0-9_-]+)', error)
        if matches:
            for match in matches:
                if match not in problem_packages:
                    problem_packages.append(match)

        logger.info(f"Identified problematic packages: {problem_packages}")

        # Remove lines containing these packages
        lines = yml.split('\n')
        fixed_lines = []

        for line in lines:
            should_remove = False
            for pkg in problem_packages:
                if pkg in line and line.strip().startswith('-'):
                    should_remove = True
                    logger.info(f"Removing line: {line.strip()}")
                    break

            if not should_remove:
                fixed_lines.append(line)

        fixed_yml = '\n'.join(fixed_lines)

        # If nothing was removed, just remove the first conda dependency as last resort
        if fixed_yml.strip() == yml.strip():
            logger.warning("Could not identify problematic package, removing first conda package...")
            lines = yml.split('\n')
            fixed_lines = []
            removed_one = False

            for line in lines:
                if not removed_one and line.strip().startswith('- ') and 'pip' not in line:
                    logger.info(f"Removing line (fallback): {line.strip()}")
                    removed_one = True
                    continue
                fixed_lines.append(line)

            fixed_yml = '\n'.join(fixed_lines)

        return fixed_yml

    def extract_fix_summary(self, original_yml: str, fixed_yml: str) -> str:
        """
        Extract a summary of what was changed.

        Args:
            original_yml: Original YAML content
            fixed_yml: Fixed YAML content

        Returns:
            Summary of changes
        """
        # Simple diff-like summary
        original_lines = set(original_yml.strip().split("\n"))
        fixed_lines = set(fixed_yml.strip().split("\n"))

        removed = original_lines - fixed_lines
        added = fixed_lines - original_lines

        summary_parts = []
        if removed:
            removed_list = [line.strip() for line in removed if line.strip()]
            summary_parts.append(f"Removed {len(removed_list)} lines: {', '.join(list(removed_list)[:3])}")
        if added:
            added_list = [line.strip() for line in added if line.strip()]
            summary_parts.append(f"Added {len(added_list)} lines")

        if not summary_parts:
            return "No changes detected"

        return "; ".join(summary_parts)
