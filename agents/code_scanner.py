"""
Code Scanner Agent.
Scans source files one by one and extracts dependency information.
This avoids token limit issues by processing files individually.
"""

import logging
from pathlib import Path
from typing import List, Set
from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


class CodeScannerAgent:
    """Scans source files one by one and builds a dependency summary."""

    SCAN_PROMPT = """Extract dependency information from this Python file.

File: {file_path}
Content:
{file_content}

List ONLY:
1. Import statements (e.g., import torch, from PIL import Image)
2. Version hints if any (e.g., # requires numpy>=1.20)
3. GPU/CUDA usage indicators (e.g., torch.cuda, tensorflow GPU, device='cuda')
4. Python version hints (e.g., match/case, typing.Literal, walrus operator)

Output format (one line per finding):
IMPORT: package_name
VERSION_HINT: package==version or package>=version
GPU: yes/no with reason
PYTHON: version requirement with reason

Be concise. No explanations. One finding per line.

Examples:
IMPORT: torch
IMPORT: transformers
VERSION_HINT: numpy>=1.20
GPU: yes, found torch.cuda.is_available()
PYTHON: >=3.10, uses match/case statement
"""

    def __init__(self, output_dir: str = "."):
        """
        Initialize CodeScannerAgent.

        Args:
            output_dir: Directory where summary file will be saved
        """
        self.client = OpenAI(api_key=settings.api_key)
        self.output_dir = Path(output_dir)
        self.summary_file = self.output_dir / "dependency_summary.txt"
        logger.info("CodeScannerAgent initialized")

    def scan_single_file(self, file_path: Path, content: str) -> str:
        """
        Analyze ONE file and return extracted dependency info.

        Args:
            file_path: Path to the file being analyzed
            content: File content

        Returns:
            Extracted information as string
        """
        # Truncate very long files to avoid token limits
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "\n... (truncated)"

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting Python dependencies from source code."
                    },
                    {
                        "role": "user",
                        "content": self.SCAN_PROMPT.format(
                            file_path=file_path.name,
                            file_content=content
                        )
                    }
                ],
                temperature=0.1,
                max_tokens=500  # Keep response short
            )

            result = response.choices[0].message.content.strip()
            logger.debug(f"Scanned {file_path.name}: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"Error scanning {file_path.name}: {e}")
            return f"ERROR scanning {file_path.name}: {str(e)}"

    def scan_dependency_file(self, file_path: Path) -> str:
        """
        Extract dependencies from requirement files without LLM.

        Args:
            file_path: Path to dependency file (requirements.txt, setup.py, etc.)

        Returns:
            Extracted information as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            info_lines = [f"\n--- Dependency File: {file_path.name} ---"]

            # Parse requirements.txt style
            if 'requirements' in file_path.name.lower():
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Extract package name and version
                        if '==' in line or '>=' in line or '<=' in line:
                            info_lines.append(f"VERSION_HINT: {line}")
                        else:
                            info_lines.append(f"IMPORT: {line}")

            # Parse setup.py
            elif file_path.name == 'setup.py':
                # Look for install_requires
                if 'install_requires' in content:
                    info_lines.append("IMPORT: (from setup.py install_requires)")
                    # Simple extraction - could be improved
                    import re
                    matches = re.findall(r'["\']([a-zA-Z0-9_-]+[>=<]*[0-9.]*)["\']', content)
                    for match in matches:
                        if '>=' in match or '==' in match or '<=' in match:
                            info_lines.append(f"VERSION_HINT: {match}")
                        elif match and not match.isdigit():
                            info_lines.append(f"IMPORT: {match}")

                # Check python_requires
                if 'python_requires' in content:
                    match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        info_lines.append(f"PYTHON: {match.group(1)}, from setup.py")

            # Parse pyproject.toml
            elif file_path.name == 'pyproject.toml':
                info_lines.append("IMPORT: (from pyproject.toml)")
                # Simple extraction
                for line in content.split('\n'):
                    if '=' in line and any(x in line for x in ['"', "'"]):
                        import re
                        matches = re.findall(r'["\']([a-zA-Z0-9_-]+[>=<]*[0-9.]*)["\']', line)
                        for match in matches:
                            if '>=' in match or '==' in match:
                                info_lines.append(f"VERSION_HINT: {match}")

            return "\n".join(info_lines)

        except Exception as e:
            logger.error(f"Error reading dependency file {file_path.name}: {e}")
            return f"ERROR reading {file_path.name}: {str(e)}"

    def initialize_summary(self):
        """Initialize/clear the summary file."""
        try:
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                f.write("# Dependency Summary\n")
                f.write("# Auto-generated by EnvAgent CodeScannerAgent\n\n")
            logger.info(f"Initialized summary file: {self.summary_file}")
        except Exception as e:
            logger.error(f"Error initializing summary file: {e}")
            raise

    def append_to_summary(self, info: str):
        """
        Append extracted info to summary file.

        Args:
            info: Information to append
        """
        try:
            with open(self.summary_file, 'a', encoding='utf-8') as f:
                f.write(info + "\n\n")
        except Exception as e:
            logger.error(f"Error appending to summary: {e}")

    def scan_all_files(self, file_paths: List[Path], project_path: Path) -> Path:
        """
        Process files one by one and build summary.

        Args:
            file_paths: List of file paths to scan
            project_path: Root project directory

        Returns:
            Path to the summary file
        """
        logger.info(f"Scanning {len(file_paths)} files...")

        # Initialize summary file
        self.initialize_summary()

        # Track what we've found
        imports_found: Set[str] = set()
        files_scanned = 0
        files_with_imports = 0

        # First, process dependency files (requirements.txt, setup.py, etc.)
        dependency_files = [f for f in file_paths if f.name in [
            'requirements.txt', 'requirements-dev.txt', 'setup.py', 'pyproject.toml'
        ]]

        for file_path in dependency_files:
            try:
                info = self.scan_dependency_file(file_path)
                self.append_to_summary(info)
                files_scanned += 1
                logger.info(f"Processed dependency file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")

        # Then, process Python source files
        python_files = [f for f in file_paths if f.suffix == '.py']

        for file_path in python_files:
            try:
                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Skip empty files
                if not content.strip():
                    continue

                # Scan with LLM
                info = self.scan_single_file(file_path, content)

                # Check if any imports found
                if 'IMPORT:' in info:
                    files_with_imports += 1
                    # Extract import names for tracking
                    for line in info.split('\n'):
                        if line.startswith('IMPORT:'):
                            pkg = line.replace('IMPORT:', '').strip()
                            imports_found.add(pkg)

                # Append to summary
                relative_path = file_path.relative_to(project_path)
                self.append_to_summary(f"\n--- {relative_path} ---\n{info}")

                files_scanned += 1

                # Log progress every 10 files
                if files_scanned % 10 == 0:
                    logger.info(f"Progress: {files_scanned}/{len(file_paths)} files scanned")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        # Write summary statistics
        summary_stats = f"""
--- SCAN SUMMARY ---
Files scanned: {files_scanned}
Files with imports: {files_with_imports}
Unique imports found: {len(imports_found)}

Imports: {', '.join(sorted(imports_found))}
"""
        self.append_to_summary(summary_stats)

        logger.info(f"Scanning complete: {files_scanned} files, {len(imports_found)} unique imports")
        logger.info(f"Summary saved to: {self.summary_file}")

        return self.summary_file
