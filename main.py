#!/usr/bin/env python3
"""
EnvAgent - Automatic Conda environment.yml generator (v2.1).
Refactored for Clean Code & Readability.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# Config & Utils
from config.settings import settings
from utils.system_checker import SystemChecker
from utils.file_filter import FileFilter
from utils import CondaExecutor, sanitize_env_name

# Agents
from agents.decision_agent import DecisionAgent
from agents.code_scanner import CodeScannerAgent
from agents.env_builder import EnvironmentBuilder
from agents.env_fixer import EnvironmentFixer
from utils.memory import Memory

# --- Setup & Helpers ---

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EnvAgent v2.1")
    parser.add_argument("source", type=str, help="Source directory to analyze")
    parser.add_argument("destination", nargs="?", default="./env_output/environment.yml", help="Output path")
    parser.add_argument("-n", "--env-name", type=str, default=None, help="Conda env name")
    parser.add_argument("--python-version", type=str, default="3.9", help="Python version")
    parser.add_argument("--no-create", action="store_true", help="Skip creation")
    return parser.parse_args()

def validate_directory(path_str: str) -> Path:
    path = Path(path_str).resolve()
    if not path.exists() or not path.is_dir():
        print(f"❌ Error: Invalid directory: {path}", file=sys.stderr)
        sys.exit(1)
    return path

# --- Core Phases ---

def run_system_check() -> None:
    """Step 0: Pre-flight system validation."""
    print("🔍 Step 0/6: Checking system requirements...")
    checker = SystemChecker()
    passed, msgs = checker.run_all_checks()
    if not passed:
        print("❌ System check failed.")
        sys.exit(1)
    print("   ✓ System checks passed\n")

def analyze_structure(root_path: Path) -> dict:
    """Step 1: Determine project structure (Monorepo detection)."""
    print("📋 Step 1/6: Analyzing project structure...")
    agent = DecisionAgent()
    decision = agent.decide(str(root_path))
    
    target_dir = Path(decision.get('target_directory', root_path))
    if target_dir != root_path:
        rel_path = target_dir.relative_to(root_path)
        print(f"   🚀 Monorepo Detected! Switching target to: ./{rel_path}")
    
    print(f"   Decision: {decision['reason']}")
    decision['target_path_obj'] = target_dir 
    return decision

def process_existing_files(decision: dict, project_name: str, py_version: str, root_path: Path, output_path: Path) -> str:
    """Case A: Handle projects with existing setup files."""
    print("\n" + "=" * 60)
    print("✅ Valid environment setup found!")
    print("=" * 60)
    
    target_dir = decision['target_path_obj']
    agent = DecisionAgent()
    
    collected_content = agent.collect_env_files_content(str(target_dir))
    
    print("\n🔨 Generating environment.yml...")
    builder = EnvironmentBuilder()
    env_content = builder.build_from_existing_files(
        collected_content=collected_content,
        project_name=project_name,
        python_version=py_version,
        target_directory=str(target_dir),
        root_directory=str(root_path)
    )
    builder.save_to_file(env_content, str(output_path))
    print(f"   ✓ Saved to: {output_path}")
    return env_content

def process_deep_analysis(target_dir: Path, output_dir: Path, project_name: str, py_version: str, output_path: Path) -> str:
    """Case B: Deep scan of source code."""
    print(f"\n   ✓ Proceeding with code analysis in: {target_dir.name}")

    # Step 2
    print("\n📁 Step 2/6: Filtering source files...")
    file_filter = FileFilter()
    relevant_files = file_filter.get_relevant_files(str(target_dir))
    
    if not relevant_files:
        print("   ⚠️  No Python files found in target directory.")
        sys.exit(1)
    print(f"   ✓ Found {len(relevant_files)} files to scan")

    # Step 3
    print("\n🔬 Step 3/6: Scanning files for dependencies...")
    scanner = CodeScannerAgent(output_dir=str(output_dir))
    summary_path = scanner.scan_files(relevant_files, target_dir, project_name=project_name)
    print(f"   ✓ Summary saved to: {summary_path.name}")

    # Step 4
    print("\n🔨 Step 4/6: Generating environment.yml...")
    builder = EnvironmentBuilder()
    env_content = builder.build_from_summary(
        summary_path=str(summary_path),
        project_name=project_name,
        python_version=py_version,
        repo_root=str(target_dir)
    )
    builder.save_to_file(env_content, str(output_path))
    print(f"   ✓ Saved to: {output_path}")
    return env_content

def create_environment_with_retry(env_name: str, output_path: Path, initial_yml: str) -> None:
    """Step 5: Create environment with self-healing loop."""
    print(f"\n🚀 Step 5/6: Creating conda environment '{env_name}'...")
    
    executor = CondaExecutor()
    fixer = EnvironmentFixer()
    builder = EnvironmentBuilder() # For saving fixed YAML

    if executor.environment_exists(env_name):
        print(f"   ⚠️  Removing existing environment...")
        executor.remove_environment(env_name)

    current_yml = initial_yml
    error_history = []
    memory = Memory()

    for attempt in range(1, settings.MAX_RETRIES + 1):
        print(f"   [Attempt {attempt}/{settings.MAX_RETRIES}]")
        
        success, error = executor.create_environment(str(output_path), env_name)

        if success:
            print("\n" + "=" * 60)
            print("✅ SUCCESS! Environment created.")
            print("=" * 60)
            print(f"Activate: conda activate {env_name}")
            return # Success exit

        # Failure Handling
        print(f"   ❌ Failed: {error[:200]}...")
        if attempt == settings.MAX_RETRIES:
            print("❌ Final failure: Max retries reached.")
            sys.exit(1)
            
        print(f"   🔧 Applying fix...")
        memory.error_history = error_history
        
        try:
            fixed_yml = fixer.fix(current_yml, error, memory)
            builder.save_to_file(fixed_yml, str(output_path))
            
            current_yml = fixed_yml
            error_history.append((error, "Applied fix"))
        except Exception as e:
            print(f"❌ Fixer crashed: {e}")
            sys.exit(1)

# --- Main Entry Point ---

def main() -> None:
    setup_logging()
    
    print("=" * 60)
    print("EnvAgent - Conda Environment Generator v2.1")
    print("Monorepo Support & Auto-Discovery Enabled")
    print("=" * 60)
    print()

    args = parse_arguments()
    root_path = validate_directory(args.source)
    output_path = Path(args.destination).resolve()
    os.makedirs(output_path.parent, exist_ok=True)
    
    # Run Pipeline
    run_system_check()
    
    decision = analyze_structure(root_path)
    target_dir = decision['target_path_obj']
    
    project_name = args.env_name if args.env_name else root_path.name
    sanitized_name = sanitize_env_name(project_name)
    
    # Generate YAML Content
    if decision["has_env_setup"] and not decision["proceed_with_analysis"]:
        env_content = process_existing_files(decision, project_name, args.python_version, root_path, output_path)
    else:
        env_content = process_deep_analysis(target_dir, output_path.parent, sanitized_name, args.python_version, output_path)
    
    # Create Environment
    if not args.no_create:
        create_environment_with_retry(sanitized_name, output_path, env_content)
    else:
        print("\n✅ Skipped creation (--no-create).")
        print(f"Run: conda env create -f {output_path}")

if __name__ == "__main__":
    main()