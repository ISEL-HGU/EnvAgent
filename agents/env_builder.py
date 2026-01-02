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

    # Original prompt for v1.0 compatibility (build from memory)
    BUILD_PROMPT = """
You are a Conda environment configuration expert. Based on the provided project analysis,
create a valid Conda environment.yml file.

Project Analysis:
- Project Name: {project_name}
- Python Version: {python_version}
- Packages: {packages}
- CUDA Version: {cuda_version}
- cuDNN Version: {cudnn_version}
- System Dependencies: {system_dependencies}

## VERSION RULES - CRITICAL:

1. **ALWAYS include version numbers** for ALL packages
2. **NEVER leave packages without versions** like `- tensorflow` or `- keras`
3. **Use specific versions** when provided in analysis: `tensorflow==2.15.0`
4. **Use recent stable versions** when version not specified:
   - tensorflow → 2.15.0
   - keras → 2.15.0
   - pytorch/torch → 2.1.0
   - numpy → 1.24.0
   - pandas → 2.1.0
   - scikit-learn → 1.3.0
   - opencv-python → 4.8.0
   - pillow → 10.0.0
   - requests → 2.31.0
   - flask → 3.0.0
   - fastapi → 0.104.0
   - transformers → 4.35.0
   - datasets → 2.14.0

5. **Ensure version compatibility**:
   - tensorflow 2.x needs keras 2.x (not 3.x)
   - pytorch 2.x needs numpy < 2.0
   - transformers needs tokenizers with compatible version

6. **Include implicit dependencies**:
   - tensorflow needs: numpy, protobuf, tensorboard
   - pytorch needs: numpy, pillow (for vision)
   - opencv-python needs: numpy
   - scikit-learn needs: numpy, scipy

## PACKAGE PLACEMENT:

1. **Install via conda** (in dependencies section):
   - python={python_version}
   - pip
   - cudatoolkit={cuda_version} (if CUDA needed)
   - cudnn (if cuDNN needed) - Use flexible version: `cudnn>=8.0` instead of exact version

   **CRITICAL - Channel Configuration:**
   - When GPU support needed, ALWAYS include nvidia channel
   - Channel order: `- nvidia`, `- conda-forge`, `- defaults`
   - This ensures proper CUDA/cuDNN package resolution

2. **Install via pip** (under pip: section):
   - All Python packages (tensorflow, pytorch, numpy, pandas, etc.)
   - Use == for exact versions
   - Example: `- tensorflow==2.15.0`

   **CRITICAL - Numpy Compatibility:**
   - For TensorFlow < 2.14, use `numpy<1.24.0` (e.g., `numpy==1.23.5`)
   - Rationale: Numpy 1.24+ removes deprecated types causing AttributeError in older TensorFlow
   - For TensorFlow >= 2.14, use `numpy>=1.24.0` (e.g., `numpy==1.24.0`)

## YAML FORMAT EXAMPLES:

### Example 1: With GPU Support (TensorFlow < 2.14)
name: {project_name}
channels:
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - cudatoolkit=11.8
  - cudnn>=8.0
  - pip
  - pip:
    - tensorflow==2.10.0
    - keras==2.10.0
    - numpy==1.23.5  # <1.24 for TF<2.14

### Example 2: With GPU Support (TensorFlow >= 2.14)
name: {project_name}
channels:
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python={python_version}
  - cudatoolkit=11.8
  - cudnn>=8.0
  - pip
  - pip:
    - tensorflow==2.15.0
    - keras==2.15.0
    - numpy==1.24.0

### Example 3: No GPU Support
name: {project_name}
channels:
  - conda-forge
  - defaults
dependencies:
  - python={python_version}
  - pip
  - pip:
    - numpy==1.24.0
    - pandas==2.1.0

## CRITICAL RULES:

1. **Environment name**: Only lowercase letters, numbers, underscores (already sanitized: {project_name})
2. **All packages MUST have versions** - NO bare package names
3. **Double-check version compatibility** between packages
4. **Include all dependencies** (both explicit and implicit)

Generate ONLY the environment.yml content, without any explanations or markdown code blocks.
The output should be ready to save directly to a file.
"""

    # New prompt for summary-based build (v2.0)
    BUILD_FROM_SUMMARY_PROMPT = """
You are a Conda environment configuration expert. Create a valid Conda environment.yml
file from this dependency summary.

Project Name: {project_name}
Suggested Python Version: {python_version}

Dependency Summary:
{summary_content}

Analyze the summary and extract:
1. All imported packages
2. Version hints if provided
3. GPU/CUDA requirements
4. Python version requirements

Then generate a valid environment.yml file.

## VERSION RULES - CRITICAL:

1. **ALWAYS include version numbers** for ALL packages
2. **NEVER leave packages without versions** like `- tensorflow` or `- keras`
3. **Use specific versions** when provided in analysis: `tensorflow==2.15.0`
4. **Use recent stable versions** when version not specified:
   - tensorflow → 2.15.0
   - keras → 2.15.0
   - pytorch/torch → 2.1.0
   - numpy → 1.24.0
   - pandas → 2.1.0
   - scikit-learn → 1.3.0
   - opencv-python → 4.8.0
   - pillow → 10.0.0
   - requests → 2.31.0
   - flask → 3.0.0
   - fastapi → 0.104.0
   - transformers → 4.35.0
   - datasets → 2.14.0

5. **Ensure version compatibility**:
   - tensorflow 2.x needs keras 2.x (not 3.x)
   - pytorch 2.x needs numpy < 2.0
   - transformers needs tokenizers with compatible version

6. **Include implicit dependencies**:
   - tensorflow needs: numpy, protobuf, tensorboard
   - pytorch needs: numpy, pillow (for vision)
   - opencv-python needs: numpy
   - scikit-learn needs: numpy, scipy

## PACKAGE PLACEMENT:

1. **Install via conda** (in dependencies section):
   - python={python_version}
   - pip
   - cudatoolkit={cuda_version} (if CUDA needed)
   - cudnn (if cuDNN needed) - Use flexible version: `cudnn>=8.0` instead of exact version

   **CRITICAL - Channel Configuration:**
   - When GPU support needed, ALWAYS include nvidia channel
   - Channel order: `- nvidia`, `- conda-forge`, `- defaults`
   - This ensures proper CUDA/cuDNN package resolution

2. **Install via pip** (under pip: section):
   - All Python packages (tensorflow, pytorch, numpy, pandas, etc.)
   - Use == for exact versions
   - Example: `- tensorflow==2.15.0`

   **CRITICAL - Numpy Compatibility:**
   - For TensorFlow < 2.14, use `numpy<1.24.0` (e.g., `numpy==1.23.5`)
   - Rationale: Numpy 1.24+ removes deprecated types causing AttributeError in older TensorFlow
   - For TensorFlow >= 2.14, use `numpy>=1.24.0` (e.g., `numpy==1.24.0`)

## YAML FORMAT EXAMPLES:

### Example 1: With GPU Support (TensorFlow < 2.14)
name: {project_name}
channels:
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - cudatoolkit=11.8
  - cudnn>=8.0
  - pip
  - pip:
    - tensorflow==2.10.0
    - keras==2.10.0
    - numpy==1.23.5  # <1.24 for TF<2.14

### Example 2: With GPU Support (TensorFlow >= 2.14)
name: {project_name}
channels:
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python={python_version}
  - cudatoolkit=11.8
  - cudnn>=8.0
  - pip
  - pip:
    - tensorflow==2.15.0
    - keras==2.15.0
    - numpy==1.24.0

### Example 3: No GPU Support
name: {project_name}
channels:
  - conda-forge
  - defaults
dependencies:
  - python={python_version}
  - pip
  - pip:
    - numpy==1.24.0
    - pandas==2.1.0

## CRITICAL RULES:

1. **Environment name**: Only lowercase letters, numbers, underscores (already sanitized: {project_name})
2. **All packages MUST have versions** - NO bare package names
3. **Double-check version compatibility** between packages
4. **Include all dependencies** (both explicit and implicit)

Generate ONLY the environment.yml content, without any explanations or markdown code blocks.
The output should be ready to save directly to a file.
"""

    def __init__(self):
        """Initialize the EnvironmentBuilder with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentBuilder initialized")

    def build(self, memory: Memory) -> str:
        """
        Generate environment.yml content from memory.

        Args:
            memory: Memory object containing analysis results

        Returns:
            Generated environment.yml content as string
        """
        logger.info("Building environment.yml...")

        # Sanitize project name for conda environment
        sanitized_name = sanitize_env_name(memory.project_name or "my_project")
        logger.info(f"Using sanitized environment name: {sanitized_name}")

        # Prepare the prompt with memory data
        prompt = self.BUILD_PROMPT.format(
            project_name=sanitized_name,
            python_version=memory.python_version or "3.9",
            packages=", ".join(memory.package_list) if memory.package_list else "none",
            cuda_version=memory.cuda_version or "not needed",
            cudnn_version=memory.cudnn_version or "not needed",
            system_dependencies=", ".join(memory.system_dependencies) if memory.system_dependencies else "none"
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in creating Conda environment files."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
            )

            env_content = response.choices[0].message.content.strip()
            logger.info("Environment.yml generated successfully")

            # Clean up any markdown code blocks if present
            if env_content.startswith("```"):
                lines = env_content.split("\n")
                # Remove first and last lines if they are code fence markers
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                env_content = "\n".join(lines)

            return env_content

        except Exception as e:
            logger.error(f"Error building environment.yml: {e}")
            raise

    def build_from_summary(self, summary_path: str, project_name: str = "my_project", python_version: str = "3.9") -> str:
        """
        Generate environment.yml content from a dependency summary file.
        This is the NEW method that works with CodeScannerAgent output.

        Args:
            summary_path: Path to the dependency summary file
            project_name: Name for the conda environment
            python_version: Python version to use (default: 3.9)

        Returns:
            Generated environment.yml content as string
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

        # Prepare prompt with summary content
        prompt = self.BUILD_FROM_SUMMARY_PROMPT.format(
            project_name=sanitized_name,
            python_version=python_version,
            summary_content=summary_content
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in creating Conda environment files."
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

    def build_from_summary_dict(self, summary: dict, project_name: str = "my_project") -> str:
        """
        Generate environment.yml from a dependency summary dictionary.
        This is the v2 method that works with DependencyCollector output.

        Args:
            summary: Dictionary with keys:
                - python_version: str
                - cuda_required: bool
                - packages: List[str]
                - version_requirements: Dict[str, str] (optional)
            project_name: Name for the conda environment

        Returns:
            Generated environment.yml content as string
        """
        logger.info(f"Building environment.yml from summary dict for project: {project_name}")

        # Sanitize project name
        sanitized_name = sanitize_env_name(project_name)

        # Format package list with versions if available
        packages_text = []
        version_reqs = summary.get('version_requirements', {})

        for package in summary['packages']:
            pkg_lower = package.lower()
            if pkg_lower in version_reqs:
                packages_text.append(f"{package}{version_reqs[pkg_lower]}")
            else:
                packages_text.append(package)

        # Build prompt
        prompt = f"""Create a Conda environment.yml file.

Project: {sanitized_name}
Python Version: {summary['python_version']}
CUDA Required: {summary['cuda_required']}
Package Count: {summary['package_count']}

Packages:
{chr(10).join(packages_text)}

## Rules:
1. Use conda-forge channel as primary
2. Add nvidia channel if CUDA required (add cudatoolkit=11.8 and cudnn>=8.0)
3. Put ML packages (torch, tensorflow, transformers) in pip section
4. Add version constraints for compatibility
5. For packages with version requirements listed above, use those versions
6. For packages without versions, use recent stable versions
7. Include implicit dependencies (e.g., torch needs pillow, tensorflow needs protobuf)

## Critical:
- ALL packages MUST have version numbers
- Check numpy compatibility with TensorFlow version
- If TensorFlow < 2.14, use numpy<1.24.0
- If TensorFlow >= 2.14, use numpy>=1.24.0

Output ONLY valid YAML, no explanations or markdown code blocks."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in creating Conda environment files."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
            )

            env_content = response.choices[0].message.content.strip()
            logger.info("Environment.yml generated successfully from summary dict")

            # Clean up any markdown code blocks
            env_content = self._clean_markdown(env_content)

            return env_content

        except Exception as e:
            logger.error(f"Error building environment.yml from summary dict: {e}")
            raise

    def _clean_markdown(self, content: str) -> str:
        """
        Remove markdown code blocks if present.

        Args:
            content: Content that may contain markdown

        Returns:
            Cleaned content
        """
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines if they are code fence markers
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines)
        return content

    def save_to_file(self, content: str, output_path: str) -> None:
        """
        Save environment.yml content to a file.

        Args:
            content: The environment.yml content
            output_path: Path where to save the file
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Environment.yml saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving environment.yml: {e}")
            raise
