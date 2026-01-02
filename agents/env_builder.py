"""
Environment Builder Agent.
Uses OpenAI GPT-4 to generate a valid Conda environment.yml file.
"""

import logging
from pathlib import Path
from openai import OpenAI

from config.settings import settings
from utils.memory import Memory
from utils.helpers import sanitize_env_name

logger = logging.getLogger(__name__)


class EnvironmentBuilder:
    """Builds a Conda environment.yml file from analysis results."""

    # ------------------------------------------------------------------
    # V2 PROMPT: LOOSE CONSTRAINTS (버전 강제 X -> 성공률 상승)
    # ------------------------------------------------------------------
    BUILD_FROM_SUMMARY_PROMPT = """
You are a Senior DevOps Engineer.
Your task is to create a robust `environment.yml` file based on the provided dependency summary.

### PROJECT DETAILS
- **Project Name:** {project_name}
- **Python Version:** {python_version}
- **CUDA Requirement:** {cuda_version}

### DETECTED DEPENDENCIES (Summary)
{summary_content}

### 🚨 STRICT RULES (Follow these to avoid errors)

1. **NO VERSION PINNING (CRITICAL):**
   - **DO NOT** use exact versions (e.g., `==1.2.3`) unless absolutely necessary or explicitly requested in summary.
   - **PREFER** no version or loose constraints (e.g., `package_name` or `package_name>=1.0`).
   - **Reason:** Hardcoded versions are the #1 cause of "ResolutionImpossible" errors in Conda.

2. **CHANNEL PRIORITY:**
   - Always include `conda-forge` and `defaults`.
   - If CUDA/GPU is needed, include `nvidia` channel FIRST.

3. **PACKAGE MAPPING:**
   - Map import names to correct package names (e.g., `cv2` → `opencv`, `sklearn` → `scikit-learn`).
   - Ensure `tiktoken` is included for OpenAI-related projects.
   - Ensure `protobuf` is included for TensorFlow projects.

4. **OUTPUT FORMAT:**
   - Return **ONLY** the raw YAML content.
   - NO markdown blocks (```yaml), NO explanations.

### TARGET OUTPUT EXAMPLE
name: {project_name}
channels:
  - conda-forge
  - defaults
dependencies:
  - python={python_version}
  - pip
  - pip:
    - numpy          # No version needed
    - pandas
    - pydantic-core
"""

    def __init__(self):
        """Initialize the EnvironmentBuilder with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentBuilder initialized")

    def build_from_summary(self, summary_path: str, project_name: str = "my_project", python_version: str = "3.9") -> str:
        """
        Generate environment.yml content from a dependency summary file.
        This is the NEW method that works with CodeScannerAgent output.
        """
        logger.info(f"Building environment.yml from summary: {summary_path}")

        # Read summary file
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_content = f.read()
        except Exception as e:
            logger.error(f"Error reading summary file: {e}")
            raise

        # Sanitize project name
        sanitized_name = sanitize_env_name(project_name)
        logger.info(f"Using sanitized environment name: {sanitized_name}")

        # -------------------------------------------------------
        # FIX: Extract CUDA info safely to prevent KeyError
        # -------------------------------------------------------
        cuda_version = "Not specified"
        if "CUDA Required: Yes" in summary_content or "True" in summary_content:
            cuda_version = "CUDA 11.8 (Auto-detected)"
        
        # Prepare prompt with summary content AND cuda_version
        prompt = self.BUILD_FROM_SUMMARY_PROMPT.format(
            project_name=sanitized_name,
            python_version=python_version,
            cuda_version=cuda_version,    # 👈 여기가 추가되었습니다!
            summary_content=summary_content
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Conda expert. Output ONLY valid YAML."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
            )

            env_content = response.choices[0].message.content.strip()
            logger.info("Environment.yml generated successfully from summary")

            # Clean up any markdown code blocks if present
            env_content = self._clean_markdown(env_content)

            return env_content

        except Exception as e:
            logger.error(f"Error building environment.yml from summary: {e}")
            raise

    def build_from_summary_dict(self, summary_dict: dict, project_name: str) -> str:
        """Helper for dictionary based summary"""
        import json
        return self.build_from_summary(json.dumps(summary_dict), project_name)

    def _clean_markdown(self, content: str) -> str:
        """Remove markdown code blocks if present."""
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()

    def save_to_file(self, content: str, output_path: str) -> None:
        """Save environment.yml content to a file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Environment.yml saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving environment.yml: {e}")
            raise