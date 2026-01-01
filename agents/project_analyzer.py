"""
Project Analyzer Agent.
Uses OpenAI GPT-4 to analyze project files and extract dependency information.
"""

import logging
import json
from typing import Dict
from openai import OpenAI

from config.settings import settings
from utils.memory import Memory

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """Analyzes project files using OpenAI GPT-4 to extract dependencies."""

    ANALYSIS_PROMPT = """
You are a Python project dependency analyzer. Analyze the provided project files and extract ALL dependencies with versions.

## YOUR TASK:

1. **PRIMARY SOURCE**: Check requirements.txt, setup.py, pyproject.toml first
2. **SECONDARY SOURCE**: Parse ALL import statements from .py files (see __extracted_imports__ summary)
3. **Map imports to packages**: cv2→opencv-python, PIL→pillow, sklearn→scikit-learn, etc.
4. **Infer versions** from code patterns when not explicitly specified
5. **Detect CUDA/GPU requirements** from code patterns

## VERSION INFERENCE RULES:

### From Code Patterns:
- `torch.cuda` or `torch.device('cuda')` → PyTorch with CUDA support, needs cudatoolkit
- `import tensorflow as tf; tf.config.list_physical_devices('GPU')` → TensorFlow with GPU
- `from typing import Optional` → Python >= 3.5
- `from typing import Literal` → Python >= 3.8
- `match/case` statements → Python >= 3.10
- `numpy.typing` → numpy >= 1.20
- `from transformers import pipeline` → transformers (recent stable version)

### Default Versions (use these if version not found):
- tensorflow → 2.15.0
- keras → 2.15.0
- torch/pytorch → 2.1.0
- numpy → 1.24.0 (BUT see compatibility rule below)
- pandas → 2.1.0
- scikit-learn → 1.3.0
- opencv-python → 4.8.0
- pillow → 10.0.0
- requests → 2.31.0
- flask → 3.0.0
- fastapi → 0.104.0

### CRITICAL - Numpy Version Compatibility:
- If TensorFlow version < 2.14 is detected → use numpy==1.23.5 (NOT 1.24+)
- If TensorFlow version >= 2.14 is detected → use numpy==1.24.0
- Rationale: Numpy 1.24+ removed deprecated types (np.object) causing AttributeError in older TensorFlow/Keras

### CUDA Detection:
- If you find `torch.cuda`, `tf.config.gpu`, or similar → cuda_version: "11.8", cudnn_version: "8.6"
- Otherwise → cuda_version: null, cudnn_version: null

## OUTPUT FORMAT (JSON):

{
    "project_name": "name of the project",
    "packages": [
        {
            "name": "tensorflow",
            "version": "2.15.0",
            "source": "pip",
            "reason": "Found 'import tensorflow' in main.py, no version in requirements.txt, using recent stable"
        },
        {
            "name": "numpy",
            "version": "1.24.0",
            "source": "conda",
            "reason": "Found in requirements.txt without version, using recent stable"
        },
        {
            "name": "opencv-python",
            "version": "4.8.0",
            "source": "pip",
            "reason": "Found 'import cv2' in utils.py, mapped to opencv-python"
        }
    ],
    "python_version": "3.9",
    "cuda_version": "11.8",
    "cudnn_version": "8.6",
    "system_dependencies": ["gcc", "libsm6"],
    "analysis_notes": "Detected GPU usage from torch.cuda calls. Using Python 3.9 as specified in setup.py."
}

## CRITICAL RULES:

1. **ALWAYS include version numbers** - NEVER leave version blank
2. **Check __extracted_imports__ first** to see all imports from .py files
3. **Map import names correctly**: cv2→opencv-python, PIL→pillow, sklearn→scikit-learn
4. **Infer versions intelligently** using code patterns and defaults above
5. **Include all discovered packages**, even if not in requirements.txt
6. **Prefer conda for ML/scientific packages** (numpy, scipy, tensorflow, pytorch)
7. **Prefer pip for pure Python packages** (requests, flask, fastapi)

Project files:
"""

    def __init__(self):
        """Initialize the ProjectAnalyzer with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("ProjectAnalyzer initialized")

    def analyze(self, files_content: Dict[str, str], memory: Memory) -> None:
        """
        Analyze project files and populate the memory with results.

        Args:
            files_content: Dictionary with filename as key and content as value
            memory: Memory object to store analysis results
        """
        logger.info("Starting project analysis...")

        # Prepare files content for the prompt
        files_text = self._format_files_content(files_content)

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Python project dependency analyzer."
                    },
                    {
                        "role": "user",
                        "content": self.ANALYSIS_PROMPT + files_text
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            # Parse response
            result_text = response.choices[0].message.content
            logger.info("Received response from OpenAI")

            # Parse JSON result
            result = json.loads(result_text)

            # Populate memory
            memory.project_name = result.get("project_name", "my_project")

            # Convert new package format to old format (list of strings)
            packages = result.get("packages", [])
            if packages and isinstance(packages[0], dict):
                # New format: list of dicts with name, version, source, reason
                memory.package_list = [
                    f"{pkg['name']}=={pkg['version']}" if pkg.get('version') else pkg['name']
                    for pkg in packages
                ]
                logger.info(f"Converted {len(packages)} packages with detailed info")
            else:
                # Old format: list of strings
                memory.package_list = packages

            memory.python_version = result.get("python_version", "3.9")
            memory.cuda_version = result.get("cuda_version")
            memory.cudnn_version = result.get("cudnn_version")
            memory.system_dependencies = result.get("system_dependencies", [])
            memory.raw_analysis = result.get("analysis_notes", "")

            logger.info(f"Analysis complete: {memory}")

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            raise

    def _format_files_content(self, files_content: Dict[str, str]) -> str:
        """
        Format files content for the prompt.

        Args:
            files_content: Dictionary with filename as key and content as value

        Returns:
            Formatted string of files content
        """
        formatted = "\n\n"

        for filename, content in files_content.items():
            formatted += f"--- {filename} ---\n"
            # Limit content length to avoid token limits
            if len(content) > 5000:
                formatted += content[:5000] + "\n... (truncated)\n"
            else:
                formatted += content + "\n"
            formatted += "\n"

        return formatted
