#!/usr/bin/env python3
"""
EnvAgent - Automatic Conda environment.yml generator (NEW ARCHITECTURE).

Token-efficient version that processes files one-by-one.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from config.settings import settings
from utils.system_checker import SystemChecker
from utils.file_filter import FileFilter
from utils import CondaExecutor, sanitize_env_name
from agents.decision_agent import DecisionAgent
from agents.code_scanner import CodeScannerAgent
from agents import EnvironmentBuilder, EnvironmentFixer


def setup_logging() -> None:
    """Configure logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="EnvAgent - Automatic Conda environment.yml generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./my_project
  %(prog)s ./my_project env.yml
  %(prog)s ./my_project test/output/env.yml
  %(prog)s . -n custom_env --no-create
        """
    )

    parser.add_argument(
        "source",
        type=str,
        help="Source directory to analyze"
    )

    parser.add_argument(
        "destination",
        nargs="?",
        default="./environment.yml",
        help="Output environment.yml path (default: ./environment.yml)"
    )

    parser.add_argument(
        "-n", "--env-name",
        type=str,
        default=None,
        help="Conda environment name (default: use project name)"
    )

    parser.add_argument(
        "--python-version",
        type=str,
        default="3.9",
        help="Python version (default: 3.9)"
    )

    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Only generate yml file, skip conda environment creation"
    )

    return parser.parse_args()


def validate_directory(directory_path: str) -> Path:
    """
    Validate that the directory exists.

    Args:
        directory_path: Path to validate

    Returns:
        Resolved Path object

    Raises:
        SystemExit: If directory doesn't exist
    """
    path = Path(directory_path).resolve()

    if not path.exists():
        print(f"Error: Directory does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    if not path.is_dir():
        print(f"Error: Path is not a directory: {path}", file=sys.stderr)
        sys.exit(1)

    return path


def main() -> None:
    """Main entry point for EnvAgent CLI."""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("=" * 60)
    print("EnvAgent - Conda Environment Generator v2.0")
    print("Token-Efficient Architecture")
    print("=" * 60)
    print()

    # Parse arguments
    args = parse_arguments()

    # Validate source directory
    directory_path = validate_directory(args.source)
    logger.info(f"Analyzing project: {directory_path}")
    print(f"📁 Project directory: {directory_path}")

    # Prepare output path and create directories if needed
    output_path = Path(args.destination).resolve()
    output_dir = output_path.parent
    if not output_dir.exists():
        logger.info(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📂 Created output directory: {output_dir}")

    print(f"📄 Output file: {output_path}")
    print()

    try:
        # ============================================================
        # STEP 0: System Pre-Check (NO LLM)
        # ============================================================
        print("🔍 Step 0/6: Checking system requirements...")
        checker = SystemChecker()
        passed, messages = checker.run_all_checks()

        for msg in messages:
            print(f"   {msg}")

        if not passed:
            print()
            print("❌ System check failed. Please fix the issues above and try again.")
            sys.exit(1)

        print("   ✓ All system checks passed")
        print()

        # ============================================================
        # STEP 1: Decision Agent
        # ============================================================
        print("📋 Step 1/6: Analyzing project structure...")
        decision_agent = DecisionAgent()
        decision = decision_agent.decide(str(directory_path))

        print(f"   Decision: {decision['reason']}")

        if decision["has_env_setup"] and not decision["proceed_with_analysis"]:
            print()
            print("=" * 60)
            print("✅ Environment file already exists!")
            print("=" * 60)
            print()
            print(f"Type: {decision['env_type']}")
            print(f"File: {decision['env_file']}")
            print()
            print("Recommendation: Use the existing environment file.")
            print()
            return

        print("   ✓ Will proceed with dependency analysis")
        print()

        # ============================================================
        # STEP 2: Filter relevant files (NO LLM)
        # ============================================================
        print("📁 Step 2/6: Filtering relevant source files...")
        file_filter = FileFilter()
        relevant_files = file_filter.get_relevant_files(str(directory_path))

        if not relevant_files:
            print("   ⚠️  No relevant files found!")
            print("   Make sure the directory contains Python files.")
            sys.exit(1)

        print(f"   ✓ Found {len(relevant_files)} relevant files")

        # Show file types
        dep_files = [f for f in relevant_files if f.name in FileFilter.ALWAYS_INCLUDE]
        py_files = [f for f in relevant_files if f.suffix == '.py']
        print(f"     - Dependency files: {len(dep_files)}")
        print(f"     - Python source files: {len(py_files)}")
        print()

        # ============================================================
        # STEP 3: Scan files one by one
        # ============================================================
        print("🔬 Step 3/6: Scanning source files for dependencies...")
        print("   (This processes files one-by-one to avoid token limits)")
        print()

        scanner = CodeScannerAgent(output_dir=str(output_dir))
        summary_path = scanner.scan_all_files(relevant_files, directory_path)

        print()
        print(f"   ✓ Dependency summary saved to: {summary_path.name}")
        print()

        # ============================================================
        # STEP 4: Build environment.yml from summary
        # ============================================================
        print("🔨 Step 4/6: Generating environment.yml...")

        # Determine project name
        project_name = args.env_name if args.env_name else directory_path.name

        builder = EnvironmentBuilder()
        env_content = builder.build_from_summary(
            summary_path=str(summary_path),
            project_name=project_name,
            python_version=args.python_version
        )

        # Save to file
        builder.save_to_file(env_content, str(output_path))

        print(f"   ✓ Saved to: {output_path}")
        print()

        # Sanitize environment name
        sanitized_env_name = sanitize_env_name(project_name)
        if sanitized_env_name != project_name:
            print(f"   ℹ️  Environment name sanitized: '{project_name}' → '{sanitized_env_name}'")
            print()

        # ============================================================
        # STEP 5: Create and validate (with retry logic)
        # ============================================================
        if not args.no_create:
            print(f"🚀 Step 5/6: Creating conda environment '{sanitized_env_name}'...")
            print(f"   (Maximum {settings.MAX_RETRIES} attempts with auto-fix)")
            print()

            conda_executor = CondaExecutor()
            fixer = EnvironmentFixer()

            # Remove environment if it already exists
            if conda_executor.environment_exists(sanitized_env_name):
                print(f"   ⚠️  Environment '{sanitized_env_name}' already exists, removing...")
                conda_executor.remove_environment(sanitized_env_name)

            current_yml = env_content
            error_history = []

            # STRICT 5 RETRY LIMIT
            for attempt in range(1, settings.MAX_RETRIES + 1):
                print(f"   [Attempt {attempt}/{settings.MAX_RETRIES}]")

                success, error = conda_executor.create_environment(str(output_path), sanitized_env_name)

                if success:
                    print()
                    print("=" * 60)
                    print("✅ SUCCESS! Environment created successfully.")
                    print("=" * 60)
                    print()
                    print("Environment details:")
                    print(f"  • Name: {sanitized_env_name}")
                    print(f"  • Config file: {output_path}")
                    print(f"  • Summary file: {summary_path}")
                    print()
                    print("Next steps:")
                    print(f"  1. Activate the environment:")
                    print(f"     conda activate {sanitized_env_name}")
                    print()
                    print(f"  2. Verify installation:")
                    print(f"     python --version")
                    print()
                    print(f"  3. Deactivate when done:")
                    print(f"     conda deactivate")
                    print()
                    break

                # Failed - log the error
                print(f"   ❌ Failed: {error[:200]}...")
                logger.error(f"Attempt {attempt} failed: {error}")

                if attempt == settings.MAX_RETRIES:
                    print()
                    print("=" * 60)
                    print(f"❌ FAILED after {settings.MAX_RETRIES} attempts")
                    print("=" * 60)
                    print()
                    print("The environment could not be created automatically.")
                    print(f"Generated file saved at: {output_path}")
                    print(f"Dependency summary at: {summary_path}")
                    print()
                    print("You can:")
                    print("1. Manually review and edit the environment.yml file")
                    print("2. Try creating it manually: conda env create -f environment.yml")
                    print("3. Check the error messages above for hints")
                    print()
                    sys.exit(1)

                # Fix and retry
                print(f"   🔧 Generating fix (attempt {attempt}/{settings.MAX_RETRIES})...")
                try:
                    # Create a minimal memory object for fixer
                    from utils.memory import Memory
                    memory = Memory()
                    memory.error_history = error_history

                    fixed_yml = fixer.fix(current_yml, error, memory)
                    fix_summary = fixer.extract_fix_summary(current_yml, fixed_yml)

                    # Save the fix
                    builder.save_to_file(fixed_yml, str(output_path))

                    # Update error history
                    error_history.append((error[:500], fix_summary))

                    # Update current yml for next iteration
                    current_yml = fixed_yml

                    print(f"   ✓ Applied fix: {fix_summary}")
                    print()

                except Exception as fix_error:
                    logger.error(f"Failed to generate fix: {fix_error}")
                    print(f"   ❌ Failed to generate fix: {fix_error}")
                    print()
                    print(f"Manual intervention required. File saved at: {output_path}")
                    sys.exit(1)
        else:
            # --no-create flag
            print("🔨 Step 5/6: Skipped (--no-create flag)")
            print()
            print("=" * 60)
            print("✅ Success! Environment file generated.")
            print("=" * 60)
            print()
            print("Next steps:")
            print(f"1. Review the generated file:")
            print(f"   cat {output_path}")
            print()
            print(f"2. Create the environment:")
            print(f"   conda env create -f {output_path}")
            print()
            print(f"3. Activate the environment:")
            print(f"   conda activate {sanitized_env_name}")
            print()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Error: {e}", file=sys.stderr)
        print()
        print("Make sure you have:")
        print("1. Created a .env file with your OPENAI_API_KEY")
        print("2. Copied .env.example to .env and added your API key")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Error: {e}", file=sys.stderr)
        print()
        print("An unexpected error occurred. Check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
