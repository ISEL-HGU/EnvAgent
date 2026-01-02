"""
Decision Agent.
First agent that analyzes project structure and decides next steps.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


class DecisionAgent:
    """Analyzes project to determine if environment files exist and next steps."""

    DECISION_PROMPT = """You are a project environment analyzer. Read the README.md and determine:

1. Does this project already have environment setup instructions?
2. What type of environment file exists or is recommended?
   - Conda (environment.yml, environment.yaml)
   - Pip (requirements.txt)
   - Docker (Dockerfile)
   - Poetry (pyproject.toml with poetry)
   - Other

README.md content:
{readme_content}

Existing files found in project:
{existing_files}

Analyze the README and existing files to determine:
- Whether environment setup is already documented
- What type of environment management is used
- Whether we should proceed with automatic analysis or use existing setup

Output JSON format:
{{
    "has_env_setup": true/false,
    "env_type": "conda" | "pip" | "docker" | "poetry" | "none",
    "env_file": "path/to/file or null",
    "proceed_with_analysis": true/false,
    "reason": "explanation of the decision"
}}

Rules:
- If environment.yml or requirements.txt exists with multiple dependencies → has_env_setup=true, proceed_with_analysis=false
- If only a README mentions setup but no files exist → has_env_setup=false, proceed_with_analysis=true
- If files exist but are empty or minimal → proceed_with_analysis=true
- Be conservative: if unsure, set proceed_with_analysis=true
"""

    # Known environment files to check
    ENV_FILES = [
        'environment.yml',
        'environment.yaml',
        'conda.yaml',
        'requirements.txt',
        'requirements-dev.txt',
        'setup.py',
        'pyproject.toml',
        'Pipfile',
        'Dockerfile'
    ]

    def __init__(self):
        """Initialize the DecisionAgent with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("DecisionAgent initialized")

    def check_existing_env_files(self, project_path: str) -> List[Dict[str, str]]:
        """
        Check if environment files already exist in project.

        Args:
            project_path: Root directory of the project

        Returns:
            List of dicts with file info: [{"name": "file.txt", "path": "path/to/file.txt", "size": 123}, ...]
        """
        project_dir = Path(project_path).resolve()
        found_files = []

        for env_file in self.ENV_FILES:
            file_path = project_dir / env_file
            if file_path.exists() and file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    found_files.append({
                        "name": env_file,
                        "path": str(file_path.relative_to(project_dir)),
                        "size": size
                    })
                    logger.info(f"Found environment file: {env_file} ({size} bytes)")
                except Exception as e:
                    logger.warning(f"Error checking {env_file}: {e}")

        return found_files

    def read_readme(self, project_path: str) -> Optional[str]:
        """
        Read README.md file if it exists.

        Args:
            project_path: Root directory of the project

        Returns:
            README content or None if not found
        """
        project_dir = Path(project_path).resolve()

        # Try different README variations
        readme_names = ['README.md', 'README.rst', 'README.txt', 'README']

        for readme_name in readme_names:
            readme_path = project_dir / readme_name
            if readme_path.exists() and readme_path.is_file():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logger.info(f"Read README from {readme_name}")
                        # Limit size to avoid token issues
                        if len(content) > 10000:
                            content = content[:10000] + "\n... (truncated)"
                        return content
                except Exception as e:
                    logger.warning(f"Error reading {readme_name}: {e}")

        logger.warning("No README file found")
        return None

    def decide(self, project_path: str) -> Dict:
        """
        Main decision logic.

        Args:
            project_path: Root directory of the project

        Returns:
            Decision dict with keys: has_env_setup, env_type, env_file, proceed_with_analysis, reason
        """
        logger.info("Analyzing project structure and making decision...")

        # Check for existing environment files
        existing_files = self.check_existing_env_files(project_path)

        # Quick decision: if substantial env files exist, recommend using them
        for file_info in existing_files:
            # If file is substantial (> 100 bytes), likely has real content
            if file_info['size'] > 100:
                # Check specific file types
                if file_info['name'] in ['environment.yml', 'environment.yaml', 'conda.yaml']:
                    return {
                        "has_env_setup": True,
                        "env_type": "conda",
                        "env_file": file_info['path'],
                        "proceed_with_analysis": False,
                        "reason": f"Found existing Conda environment file: {file_info['name']} ({file_info['size']} bytes). You can use it directly with: conda env create -f {file_info['name']}"
                    }
                elif file_info['name'] == 'requirements.txt':
                    return {
                        "has_env_setup": True,
                        "env_type": "pip",
                        "env_file": file_info['path'],
                        "proceed_with_analysis": False,
                        "reason": f"Found existing pip requirements file: {file_info['name']} ({file_info['size']} bytes). You can use it directly with: pip install -r {file_info['name']}"
                    }

        # Read README for more context
        readme_content = self.read_readme(project_path)

        if not readme_content:
            # No README, no substantial env files → proceed with analysis
            return {
                "has_env_setup": False,
                "env_type": "none",
                "env_file": None,
                "proceed_with_analysis": True,
                "reason": "No README or environment files found. Will analyze source code to generate environment.yml"
            }

        # Use LLM to analyze README + existing files
        try:
            # Format existing files info
            if existing_files:
                files_text = "\n".join([
                    f"- {f['name']} ({f['size']} bytes)"
                    for f in existing_files
                ])
            else:
                files_text = "None found"

            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing Python projects and their environment setup."
                    },
                    {
                        "role": "user",
                        "content": self.DECISION_PROMPT.format(
                            readme_content=readme_content,
                            existing_files=files_text
                        )
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            # Parse response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info(f"Decision made: {result}")
            return result

        except Exception as e:
            logger.error(f"Error making decision: {e}")
            # Fallback: proceed with analysis
            return {
                "has_env_setup": False,
                "env_type": "none",
                "env_file": None,
                "proceed_with_analysis": True,
                "reason": f"Error analyzing project (fallback to analysis): {str(e)}"
            }
