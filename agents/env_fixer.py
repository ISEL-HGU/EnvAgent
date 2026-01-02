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
Your goal is to fix the error by relaxing constraints, NOT by removing essential packages.

## CURRENT environment.yml:
{current_yml}

## CONDA ERROR:
{error_message}

## PREVIOUS FIX ATTEMPTS:
{error_history}

## 🚨 CRITICAL STRATEGY (FOLLOW THIS ORDER):

1. **Dependency Conflicts / UnsatisfiableError / Pip failed:**
   - **PRIMARY SOLUTION:** REMOVE STRICT VERSION CONSTRAINTS.
   - Change `package==1.2.3` to just `package`.
   - Change `package>=1.0` to just `package`.
   - **Reasoning:** Let Conda/Pip resolve the compatible versions. Do NOT guess new version numbers.

2. **PackagesNotFoundError:**
   - First, remove the version constraint.
   - If that fails, check if the package belongs in the `pip:` section.
   - Only remove the package if it looks non-essential (e.g., plotting tools, linters).

3. **"transformers" or "tokenizers" or "protobuf" Errors:**
   - These are notorious for conflicts. REMOVE their version numbers immediately.
   - Example: `transformers==4.30.0` -> `transformers`

4. **CUDA/GPU Issues:**
   - Ensure `channels` includes `- nvidia` if `cudatoolkit` or `cudnn` is used.
   - Remove versions for `cudnn` and `cudatoolkit`.

## YOUR TASK:
Return the FIXED YAML.
- DO NOT return the same YAML.
- DO NOT use markdown code blocks (```).
- RETURN ONLY THE YAML CONTENT.
"""

    def __init__(self):
        """Initialize the EnvironmentFixer with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentFixer initialized")

    def fix(self, current_yml: str, error_message: str, memory: Memory) -> str:
        """
        Generate a fixed environment.yml based on the error.
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
                        "content": "You are an expert DevOps engineer. Your #1 rule for fixing dependency conflicts is removing version numbers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Low temperature for deterministic fixes
            )

            fixed_yml = response.choices[0].message.content.strip()

            # Clean up any markdown code blocks if present
            if fixed_yml.startswith("```"):
                lines = fixed_yml.split("\n")
                # Remove first line if it's ```yaml or ```
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove last line if it's ```
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
            # If API fails, try manual fix
            return self._force_remove_problematic_package(current_yml, error_message)

    def _are_yamls_identical(self, yml1: str, yml2: str) -> bool:
        """Check if two YAML contents are identical (ignoring whitespace)."""
        def normalize(yml):
            lines = [line.strip() for line in yml.strip().split("\n") if line.strip()]
            return "\n".join(sorted(lines))

        return normalize(yml1) == normalize(yml2)

    def _force_remove_problematic_package(self, yml: str, error: str) -> str:
        """
        Fallback: Forcefully fix the problematic package.
        Strategy:
        1. STRIP VERSIONS (e.g., numpy==1.21 -> numpy)
        2. If that fails, remove the package.
        """
        logger.info("Forcing fix for problematic package...")
        lines = yml.split('\n')
        fixed_lines = []
        
        # 1. Identify problematic packages from error message
        problem_packages = []
        matches = re.findall(r'["\']([a-zA-Z0-9_-]+)(?:==|>=|<=)?[0-9.]*["\']', error)
        if matches:
            problem_packages.extend([m for m in matches if m not in problem_packages])
        
        # Look for "- package" pattern
        matches = re.findall(r'- ([a-zA-Z0-9_-]+)', error)
        if matches:
            problem_packages.extend([m for m in matches if m not in problem_packages])

        # Common suspects for "pip failed" without clear names
        if "Pip failed" in error and not problem_packages:
            logger.info("Pip failed but no package named. Stripping versions from ALL pip packages.")
            problem_packages = ["ALL_PIP"]

        logger.info(f"Identified problematic targets: {problem_packages}")

        # 2. Apply fixes
        in_pip_section = False
        for line in lines:
            stripped_line = line.strip()
            
            if stripped_line == "pip:":
                in_pip_section = True
                fixed_lines.append(line)
                continue
            
            if not stripped_line.startswith("-"):
                in_pip_section = False
                fixed_lines.append(line)
                continue

            # Check if this line needs fixing
            should_fix = False
            package_name = stripped_line.replace("-", "").strip().split("=")[0].split(">")[0].split("<")[0]
            
            if "ALL_PIP" in problem_packages and in_pip_section:
                should_fix = True
            elif any(pkg in stripped_line for pkg in problem_packages):
                should_fix = True

            if should_fix:
                # STRATEGY: Strip Version Constraints (Keep package name)
                if "==" in line or ">=" in line or "<=" in line:
                    # Get indentation
                    indent = line[:line.find("-")]
                    new_line = f"{indent}- {package_name}"
                    logger.info(f"Relaxing constraint: {stripped_line} -> {package_name}")
                    fixed_lines.append(new_line)
                else:
                    # Already no version? Maybe remove it if it was explicitly flagged as not found
                    if "PackagesNotFoundError" in error:
                        logger.info(f"Removing not found package: {stripped_line}")
                        pass # Skip adding this line (delete it)
                    else:
                        fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)
    
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
            # Show up to 3 removed items
            summary_parts.append(f"Removed/Changed {len(removed_list)} lines: {', '.join(list(removed_list)[:3])}")
        
        if added:
            added_list = [line.strip() for line in added if line.strip()]
            summary_parts.append(f"Added/Updated {len(added_list)} lines")

        if not summary_parts:
            return "No obvious changes detected (formatting only?)"

        return "; ".join(summary_parts)