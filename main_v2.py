#!/usr/bin/env python3
"""
EnvAgent v2 - Conda environment.yml generator with DependencyCollector.

This version uses DependencyCollector to avoid token limits by:
1. Processing files one-by-one (NO LLM)
2. Collecting imports and dependencies
3. Sending only the summary to LLM (not all file contents)

Key benefit: 355,000 tokens → ~500 tokens
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from config.settings import settings
from utils import LocalReader, DependencyCollector, CondaExecutor, sanitize_env_name
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
        description="EnvAgent v2 - Automatic Conda environment.yml generator (with DependencyCollector)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./my_project
  %(prog)s ./my_project env.yml
  %(prog)s ./my_project --no-create
  %(prog)s . -n custom_env
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
    """Main entry point for EnvAgent v2 CLI."""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("=" * 60)
    print("EnvAgent v2 - Conda Environment Generator")
    print("Token-Efficient with DependencyCollector")
    print("=" * 60)
    print()

    # Parse arguments
    args = parse_arguments()

    # Validate source directory
    directory_path = validate_directory(args.source)
    logger.info(f"Analyzing project: {directory_path}")
    print(f"📁 Project directory: {directory_path}")

    # Prepare output path
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
        # STEP 1: Read project files (with expanded EXCLUDE_DIRS)
        # ============================================================
        print("📖 Step 1/5: Reading project files...")
        reader = LocalReader(str(directory_path))
        files_content = reader.read_files()

        if not files_content:
            print("⚠️  Warning: No relevant files found in the directory.")
            print("Make sure the directory contains Python files or dependency files.")
            sys.exit(1)

        print(f"   Found {len(files_content)} files to analyze")
        print()

        # ============================================================
        # STEP 2: Collect dependencies (NO LLM - pure Python!)
        # ============================================================
        print("🔍 Step 2/5: Collecting dependencies (without LLM)...")

        # Initialize collector
        summary_file = output_path.parent / "dependency_summary.txt"
        collector = DependencyCollector(output_file=str(summary_file))

        # Process each file
        for filepath, content in files_content.items():
            collector.process_file(filepath, content)

        # Get summary
        summary = collector.get_summary()

        # Save summary file
        saved_summary = collector.save_summary()

        print(f"   ✓ Processed {summary['files_processed']} files")
        print(f"   ✓ Found {summary['package_count']} unique packages")
        print(f"   ✓ Python version: {summary['python_version']}")
        print(f"   ✓ CUDA required: {summary['cuda_required']}")
        print(f"   ✓ Summary saved to: {saved_summary}")
        print()

        # ============================================================
        # STEP 3: Build environment.yml with LLM (using summary only!)
        # ============================================================
        print("🔨 Step 3/5: Building environment.yml with LLM...")
        print("   (Sending only summary, not all file contents)")

        # Determine project name
        project_name = args.env_name if args.env_name else directory_path.name

        # Build environment.yml from summary
        builder = EnvironmentBuilder()
        env_content = builder.build_from_summary_dict(summary, project_name)

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
        # STEP 4: Create and validate (with retry logic)
        # ============================================================
        if not args.no_create:
            print(f"🚀 Step 4/5: Creating conda environment '{sanitized_env_name}'...")
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
                    print(f"  • Summary file: {saved_summary}")
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
                    print(f"Dependency summary at: {saved_summary}")
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
                    # Create minimal memory for fixer
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
            print("🔨 Step 4/5: Skipped (--no-create flag)")
            print()
            print("=" * 60)
            print("✅ Success! Environment file generated.")
            print("=" * 60)
            print()
            print("Next steps:")
            print(f"1. Review the generated file:")
            print(f"   cat {output_path}")
            print()
            print(f"2. Review the dependency summary:")
            print(f"   cat {saved_summary}")
            print()
            print(f"3. Create the environment:")
            print(f"   conda env create -f {output_path}")
            print()
            print(f"4. Activate the environment:")
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
