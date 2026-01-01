# EnvAgent Quick Reference

## Overview

EnvAgent automatically generates Conda environment.yml files by analyzing your Python project.

**Key Features:**
- ✅ Analyzes ALL Python imports (not just requirements.txt)
- ✅ Maps import names to packages (cv2→opencv-python, sklearn→scikit-learn)
- ✅ Infers versions from code patterns or uses stable defaults
- ✅ ALWAYS includes version numbers (no bare `- tensorflow`)
- ✅ Auto-fixes conda errors (up to 5 attempts)
- ✅ Detects CUDA/GPU requirements automatically
- ✅ Sanitizes environment names (spaces→underscores)

## Basic Usage

```bash
# Generate and create environment
python3 main.py ./my_project

# Generate and create with custom output
python3 main.py ./my_project output.yml

# Custom environment name
python3 main.py ./my_project output.yml -n my_custom_env

# Only generate YAML (don't create environment)
python3 main.py ./my_project output.yml --no-create
```

## What Gets Analyzed

### Files Read
- ✅ requirements.txt
- ✅ setup.py
- ✅ pyproject.toml
- ✅ README.md
- ✅ ALL .py files (for imports)

### Excluded Directories
- ❌ `__pycache__`, `.git`, `venv`, `env`, `node_modules`
- ❌ `.pytest_cache`, `.tox`, `build`, `dist`

## Import Detection

EnvAgent extracts ALL import statements from your Python files:

```python
# Your code
import numpy as np
from sklearn.model_selection import train_test_split
import cv2
import PIL
```

**Detected Packages:**
- `numpy` → numpy==1.24.0
- `sklearn` → scikit-learn==1.3.0
- `cv2` → opencv-python==4.8.0
- `PIL` → pillow==10.0.0

## Version Inference

### Priority Order
1. **Explicit versions** in requirements.txt/setup.py
2. **Code pattern detection** (torch.cuda, typing.Literal, etc.)
3. **Stable defaults** (tensorflow→2.15.0, numpy→1.24.0)

### Code Pattern Examples

```python
# Detects CUDA requirement
import torch
device = torch.device('cuda')  # → cudatoolkit=11.8

# Detects Python version
from typing import Literal  # → python >= 3.8
match x:  # → python >= 3.10
    case 1: pass

# Detects minimum versions
import numpy.typing  # → numpy >= 1.20
```

## Auto-Fix System

If conda environment creation fails, EnvAgent automatically:

1. ✅ Analyzes the error
2. ✅ Generates a fix (removes problematic packages, adjusts versions)
3. ✅ Retries creation (up to 5 attempts)
4. ✅ Shows debug output (BEFORE and AFTER YAML)

### Special: Smart cuDNN Error Handling

For cuDNN PackagesNotFoundError, uses 4-strategy fix:

**Strategy 1: Add nvidia channel**
```
🔧 Generating fix (attempt 1/5)...
Detected cudnn error - applying smart fixes...
Adding nvidia channel to resolve cudnn...
✓ Applied fix: Added nvidia channel
```

**Strategy 2: Relax version constraint**
```
🔧 Generating fix (attempt 2/5)...
Relaxing cudnn version constraint: cudnn=8.6 → cudnn>=8.0
✓ Applied fix: Relaxed cudnn version to cudnn>=8.0
```

**Strategy 3: Remove version entirely**
```
🔧 Generating fix (attempt 3/5)...
Simplified cudnn: cudnn>=8.0 → cudnn
✓ Applied fix: Removed cudnn version constraint
```

**Strategy 4: Remove cuDNN (last resort)**
```
🔧 Generating fix (attempt 4/5)...
✓ Applied fix: Removed cudnn (included in cudatoolkit)
```

**Example:**
```
[Attempt 1/5]
❌ Failed: PackagesNotFoundError: cudnn=8.6

🔧 Generating fix (attempt 1/5)...
Detected cudnn error - applying smart fixes...
Adding nvidia channel to resolve cudnn...
✓ Applied fix: Added nvidia channel

[Attempt 2/5]
❌ Failed: PackagesNotFoundError: cudnn=8.6

🔧 Generating fix (attempt 2/5)...
Relaxing cudnn version constraint from: - cudnn=8.6
Changed to: - cudnn>=8.0
✓ Applied fix: Relaxed cudnn version to cudnn>=8.0

[Attempt 3/5]
✅ SUCCESS!
```

## Environment Name Sanitization

Invalid conda names are automatically fixed:

| Input | Output |
|-------|--------|
| `ML Test Project` | `ml_test_project` |
| `My-App@v2.0` | `my_appv20` |
| `project#123` | `project123` |
| `123project` | `env_123project` |

**Notification shown:**
```
ℹ️  Environment name sanitized: 'ML Test Project' → 'ml_test_project'
```

## Output Examples

### GPU Environment (TensorFlow 2.10)

```yaml
name: ml_project
channels:
  - nvidia          # ← Automatically added for GPU support
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - cudatoolkit=11.8
  - cudnn>=8.0      # ← Flexible version to avoid errors
  - pip
  - pip:
    - tensorflow==2.10.0
    - keras==2.10.0
    - numpy==1.23.5  # ← Compatible with TF < 2.14
    - tensorflow-probability==0.18.0
```

### GPU Environment (TensorFlow 2.15)

```yaml
name: ml_project
channels:
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - cudatoolkit=11.8
  - cudnn>=8.0
  - pip
  - pip:
    - tensorflow==2.15.0
    - keras==2.15.0
    - numpy==1.24.0  # ← OK for TF >= 2.14
    - pandas==2.1.0
    - scikit-learn==1.3.0
    - opencv-python==4.8.0
```

### CPU-Only Environment

```yaml
name: ml_project
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - pip
  - pip:
    - numpy==1.24.0
    - pandas==2.1.0
    - scikit-learn==1.3.0
```

### Next Steps Output

```
✅ SUCCESS! Environment created successfully.

Environment details:
  • Name: ml_project
  • Config file: /path/to/environment.yml

Next steps:
  1. Activate the environment:
     conda activate ml_project

  2. Verify installation:
     python --version

  3. Deactivate when done:
     conda deactivate
```

## Import Name Mappings

Common import-to-package mappings:

| Import | Package |
|--------|---------|
| `cv2` | opencv-python |
| `PIL` | pillow |
| `sklearn` | scikit-learn |
| `skimage` | scikit-image |
| `yaml` | pyyaml |
| `dotenv` | python-dotenv |
| `bs4` | beautifulsoup4 |
| `torch` | pytorch |
| `transformers` | transformers |

Full list: 56 mappings in [utils/helpers.py:IMPORT_TO_PACKAGE](utils/helpers.py)

## Default Versions

When version not specified, uses recent stable:

| Package | Default Version |
|---------|----------------|
| tensorflow | 2.15.0 |
| keras | 2.15.0 |
| pytorch/torch | 2.1.0 |
| numpy | 1.24.0 |
| pandas | 2.1.0 |
| scikit-learn | 1.3.0 |
| opencv-python | 4.8.0 |
| pillow | 10.0.0 |
| requests | 2.31.0 |
| transformers | 4.35.0 |

## GPU Support & Deep Learning

### Automatic GPU Detection

EnvAgent automatically detects GPU requirements from code:

```python
# Detects CUDA requirement
import torch
device = torch.device('cuda')  # → Adds cudatoolkit + cudnn

# Detects TensorFlow GPU
import tensorflow as tf
tf.config.list_physical_devices('GPU')  # → Adds CUDA support
```

**Generated environment.yml:**
```yaml
channels:
  - nvidia          # ← Added automatically
  - conda-forge
  - defaults
dependencies:
  - cudatoolkit=11.8
  - cudnn>=8.0      # ← Flexible version
```

### Numpy Compatibility

EnvAgent automatically selects compatible numpy versions:

| TensorFlow Version | Numpy Version | Reason |
|-------------------|---------------|--------|
| < 2.14 | 1.23.5 | Avoid AttributeError from removed np.object |
| >= 2.14 | 1.24.0 | Compatible with newer numpy |

**Example for TensorFlow 2.10:**
```yaml
- pip:
  - tensorflow==2.10.0
  - numpy==1.23.5      # ← Automatically downgraded
```

### cuDNN Error Resolution

Common error:
```
PackagesNotFoundError: cudnn=8.6
```

**Automatic fixes applied:**
1. Add nvidia channel
2. Relax to `cudnn>=8.0`
3. Use bare `cudnn`
4. Remove cuDNN (included in cudatoolkit)

See [CUDNN_FIX_GUIDE.md](CUDNN_FIX_GUIDE.md) for details.

## Troubleshooting

### "No relevant files found"
- Make sure directory contains .py files or requirements.txt
- Check that you're not pointing to a build/dist directory

### "PackagesNotFoundError: cudnn"
- EnvAgent will automatically fix this (see Auto-Fix System above)
- Adds nvidia channel and relaxes version constraints
- Usually resolved in 2-3 attempts

### "FAILED after 5 attempts"
- Manually review the generated environment.yml
- Some packages may not be available for your platform
- Check error messages for hints
- For cuDNN errors, see [CUDNN_FIX_GUIDE.md](CUDNN_FIX_GUIDE.md)

### "AttributeError: module 'numpy' has no attribute 'object'"
- This occurs with TensorFlow < 2.14 and numpy >= 1.24
- EnvAgent automatically prevents this by using numpy==1.23.5
- If you see this error, the analyzer may have missed the TensorFlow version

### "Environment name sanitized"
- This is normal for names with spaces/special characters
- Use the sanitized name when activating: `conda activate ml_project`

### Missing API Key
```
Error: OPENAI_API_KEY not found
```
- Create a `.env` file in the project root
- Add your API key: `OPENAI_API_KEY=sk-...`

## Configuration

### .env File

Required environment variable:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### Settings

Located in [config/settings.py](config/settings.py):

```python
MAX_RETRIES = 5  # Number of auto-fix attempts
```

## Files Generated

1. **environment.yml** - Conda environment configuration
2. **Logs** - Detailed logging in console and logger output

## Advanced Usage

### Multiple Projects

```bash
# Project 1
python3 main.py ./project1 envs/project1.yml -n project1

# Project 2
python3 main.py ./project2 envs/project2.yml -n project2
```

### CI/CD Integration

```bash
# Generate only (for review)
python3 main.py . environment.yml --no-create

# Review the file
cat environment.yml

# Create manually
conda env create -f environment.yml
```

### Testing Before Deployment

```bash
# Generate test environment
python3 main.py . test-env.yml -n test_env

# Test it
conda activate test_env
pytest
conda deactivate
```

## Help

```bash
python3 main.py --help
```

**Output:**
```
usage: main.py [-h] [-n ENV_NAME] [--no-create] source [destination]

EnvAgent - Automatic Conda environment.yml generator

positional arguments:
  source                Source directory to analyze
  destination           Output environment.yml path (default: ./environment.yml)

optional arguments:
  -h, --help            show this help message and exit
  -n ENV_NAME, --env-name ENV_NAME
                        Conda environment name (default: use project name)
  --no-create           Only generate yml file, skip conda environment creation
```

## Documentation

### Getting Started
- [README.md](README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [USAGE.md](USAGE.md) - Detailed usage examples
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - This file

### Feature Guides
- [AUTO_FIX_GUIDE.md](AUTO_FIX_GUIDE.md) - Auto-fix system details
- [CUDNN_FIX_GUIDE.md](CUDNN_FIX_GUIDE.md) - **NEW:** cuDNN error handling (4-strategy fix)
- [IMPORT_ANALYSIS_IMPROVEMENT.md](IMPORT_ANALYSIS_IMPROVEMENT.md) - Import analysis & version inference
- [ENV_NAME_SANITIZATION.md](ENV_NAME_SANITIZATION.md) - Name sanitization docs

### Technical Details
- [ENV_FIXER_DEBUG.md](ENV_FIXER_DEBUG.md) - Debugging improvements
- [NEXT_STEPS_FIX.md](NEXT_STEPS_FIX.md) - Next steps display fix
- [CUDNN_IMPROVEMENTS_SUMMARY.md](CUDNN_IMPROVEMENTS_SUMMARY.md) - **NEW:** GPU support improvements

## Support

For issues or questions:
- Check existing documentation
- Review error messages and logs
- Verify .env file has valid OPENAI_API_KEY
- Try with --no-create flag to see generated YAML
