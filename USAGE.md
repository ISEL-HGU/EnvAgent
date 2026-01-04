# EnvAgent Usage Guide

Complete guide for using EnvAgent v2.0 - Token-Efficient Architecture

## Quick Start

### 1. Installation

```bash
# Navigate to the EnvAgent directory
cd EnvAgent

# Install required packages
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
nano .env  # Add your OpenAI API key
```

### 2. Configure API Key

Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Run EnvAgent

```bash
# Analyze current directory
python main.py .

# Analyze specific project
python main.py /path/to/your/project

# Specify custom output file
python main.py /path/to/your/project my_env.yml

# Custom environment name
python main.py /path/to/your/project -n my_custom_name
```

---

## Command Line Reference

### Full Syntax

```
python main.py <source> [destination] [options]
```

### Arguments

**Positional Arguments:**

- `source` (required)
  - Source directory to analyze
  - Can be absolute or relative path
  - Examples: `.`, `~/my_project`, `/home/user/code/app`

- `destination` (optional)
  - Output path for environment.yml
  - Default: `./environment.yml`
  - Automatically creates parent directories if needed
  - Examples: `env.yml`, `output/env.yml`, `test/output/env.yml`

**Optional Arguments:**

- `-n NAME`, `--env-name NAME`
  - Custom conda environment name
  - Default: Uses project directory name
  - Example: `-n my_ml_env`

- `--python-version VERSION`
  - Python version to use in environment
  - Default: `3.9`
  - Example: `--python-version 3.10`

- `--no-create`
  - Generate environment.yml WITHOUT creating conda environment
  - Useful for reviewing before creation
  - No value needed (flag only)

- `-h`, `--help`
  - Show help message and exit

### Examples

```bash
# Basic - analyze current directory
python main.py .

# Specify project directory
python main.py /path/to/project

# Custom output location
python main.py /path/to/project custom_env.yml

# Custom environment name
python main.py /path/to/project -n myproject

# Custom Python version
python main.py /path/to/project --python-version 3.10

# Only generate yml, don't create environment
python main.py /path/to/project --no-create

# Combine multiple options
python main.py ~/ml_project output/env.yml -n ml_env --python-version 3.10

# Output to subdirectory (auto-creates directory)
python main.py ~/project test/output/env.yml -n test_env
```

---

## What Gets Analyzed?

EnvAgent v2.0 uses a **token-efficient file-by-file approach** to analyze your project.

### Configuration Files (Always Included)

These files are analyzed first for explicit dependency information:
- `requirements.txt` - Python package requirements
- `setup.py` - Package installation scripts
- `pyproject.toml` - Modern Python project configurations
- `README.md` - Project documentation

### Python Source Files

All `.py` files in the project directory, **excluding**:
- `__pycache__/` - Python bytecode cache
- `.git/` - Git repository data
- `venv/`, `env/`, `ENV/` - Virtual environments
- `node_modules/` - Node.js dependencies (if any)
- `.pytest_cache/` - Pytest cache
- `build/`, `dist/` - Build artifacts

### What EnvAgent Detects

From your files, EnvAgent automatically detects:
- ✅ Python package names (numpy, pandas, tensorflow, etc.)
- ✅ Package versions (explicit or constraints)
- ✅ Python version requirements
- ✅ CUDA/cuDNN requirements (for ML/DL projects)
- ✅ Conda vs pip packages
- ✅ Version constraints (`==`, `>=`, `~=`)

---

## Complete Workflow Example

### Step-by-Step: Machine Learning Project

```bash
# 1. Analyze your ML project
python main.py ~/my_ml_project
```

**EnvAgent Output:**

```
============================================================
EnvAgent - Conda Environment Generator v2.0
Token-Efficient Architecture
============================================================

📁 Project directory: /home/user/my_ml_project
📄 Output file: ./environment.yml

🔍 Step 0/6: Checking system requirements...
   ✓ conda is installed
   ✓ All system checks passed

📋 Step 1/6: Analyzing project structure...
   Decision: No existing environment found
   ✓ Will proceed with dependency analysis

📁 Step 2/6: Filtering relevant source files...
   ✓ Found 18 relevant files
     - Dependency files: 2
     - Python source files: 16

🔬 Step 3/6: Scanning source files for dependencies...
   (This processes files one-by-one to avoid token limits)
   [1/18] Analyzing requirements.txt
   [2/18] Analyzing README.md
   [3/18] Analyzing train.py
   ...
   ✓ Dependency summary saved to: dependency_summary.txt

🔨 Step 4/6: Generating environment.yml...
   ✓ Saved to: ./environment.yml

🚀 Step 5/6: Creating conda environment 'my_ml_project'...
   (Maximum 8 attempts with auto-fix)
   [Attempt 1/8]
   Creating environment...

============================================================
✅ SUCCESS! Environment created successfully.
============================================================

Environment details:
  • Name: my_ml_project
  • Config file: ./environment.yml
  • Summary file: dependency_summary.txt

Next steps:
  1. Activate the environment:
     conda activate my_ml_project

  2. Verify installation:
     python --version

  3. Deactivate when done:
     conda deactivate
```

```bash
# 2. Activate the environment
conda activate my_ml_project

# 3. Verify packages are installed
python -c "import tensorflow, numpy, pandas; print('All packages loaded!')"

# 4. Run your project
python train.py
```

---

## Generated File Structure

EnvAgent generates a standard conda `environment.yml` file:

```yaml
name: my_ml_project
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - cudatoolkit=11.8
  - cudnn=8.6
  - pip
  - pip:
    - numpy==1.24.0
    - pandas>=2.0.0
    - tensorflow==2.13.0
    - scikit-learn>=1.3.0
    - matplotlib>=3.5.0
```

**File Breakdown:**

- `name:` - Environment name (from project directory or `-n` flag)
- `channels:` - Conda channels (conda-forge for most packages)
- `dependencies:` - Top-level conda packages
  - `python=X.X` - Python version
  - `cudatoolkit=X.X` - CUDA if needed (ML projects)
  - `cudnn=X.X` - cuDNN if needed (ML projects)
  - `pip` - Pip package manager
  - `pip:` - Python packages installed via pip

---

## Auto-Fix Feature

EnvAgent v2.0 includes **automatic error fixing** with up to **8 retry attempts**.

### How It Works

When conda environment creation fails:

1. **Error Detection** - EnvAgent captures the conda error message
2. **AI Diagnosis** - GPT-4 analyzes the error and suggests fixes
3. **Auto-Fix** - Automatically updates environment.yml with the fix
4. **Retry** - Attempts to create the environment again
5. **Repeat** - Up to 8 times until success or max retries reached

### Common Fixes Applied

- **Version conflicts** - Adjusts incompatible version constraints
- **Missing packages** - Adds missing dependencies
- **Channel issues** - Switches between conda-forge and defaults
- **CUDA mismatches** - Adjusts CUDA/cuDNN versions for compatibility
- **Platform issues** - Removes platform-specific packages

### Example Auto-Fix Session

```
🚀 Step 5/6: Creating conda environment 'my_project'...
   (Maximum 8 attempts with auto-fix)

   [Attempt 1/8]
   ❌ Failed: PackagesNotFoundError: tensorflow==2.14.0

   🔧 Generating fix (attempt 1/8)...
   ✓ Applied fix: Changed tensorflow==2.14.0 to tensorflow==2.13.0

   [Attempt 2/8]
   ❌ Failed: Conflict: numpy>=1.25 vs <1.24

   🔧 Generating fix (attempt 2/8)...
   ✓ Applied fix: Adjusted numpy version to ==1.24.3

   [Attempt 3/8]
   ✅ Success! Environment created.
```

### When Auto-Fix Fails

If all 8 attempts fail:
1. EnvAgent saves the latest `environment.yml`
2. Shows the last error message
3. Provides manual troubleshooting steps

You can then:
- Manually edit `environment.yml`
- Create environment manually: `conda env create -f environment.yml`
- Review error messages for hints

## Troubleshooting

### Error: OPENAI_API_KEY not found

**Solution**: Make sure you've created a `.env` file with your API key:
```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your_key_here
```

### Error: Directory does not exist

**Solution**: Check the path is correct:
```bash
# Use absolute path
python main.py /full/path/to/project

# Or relative path
python main.py ../my_project
```

### No relevant files found

**Solution**: Ensure your project contains:
- At least one `.py` file, or
- A `requirements.txt`, `setup.py`, or `pyproject.toml`

### API Rate Limits

**Solution**: If you hit OpenAI rate limits:
- Wait a moment and try again
- Consider using a different API key tier
- Check your OpenAI usage dashboard

## Advanced Usage

### Custom Python Version

If the detected Python version is incorrect, manually edit the generated `environment.yml`:

```yaml
dependencies:
  - python=3.10  # Change to your preferred version
```

### Adding Additional Packages

After generation, you can manually add packages:

```yaml
dependencies:
  - pip
  - pip:
    - numpy==1.24.0
    - your-custom-package  # Add here
```

### Multiple Environments

Generate different environments for different purposes:

```bash
# Development environment
python main.py . -o env_dev.yml

# Production environment (then manually edit)
python main.py . -o env_prod.yml
```

## Best Practices

1. **Review before using**: Always review the generated file before creating the environment

2. **Pin versions**: For reproducibility, ensure versions are pinned in your source files

3. **Test the environment**: After creation, test that all imports work:
   ```bash
   conda activate my_project
   python -c "import numpy, pandas, tensorflow"
   ```

4. **Version control**: Commit the generated `environment.yml` to your repository

5. **Update regularly**: Re-run EnvAgent when you add new dependencies

## Integration with Existing Workflows

### Git Workflow

```bash
# Generate environment file
python main.py .

# Add to git
git add environment.yml
git commit -m "Add conda environment specification"
git push
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Create Conda environment
  run: conda env create -f environment.yml
```

## Getting Help

```bash
# Show help
python main.py --help

# View version and info
python main.py --version  # Not implemented yet
```

## Tips for Better Results

1. **Include a README**: A well-written README with requirements helps the AI
2. **Use requirements.txt**: Explicit dependencies are better detected
3. **Add comments**: Comments in code about special dependencies help
4. **Specify versions**: Include version constraints when important

---

## Common Use Cases

### Use Case 1: New Project Setup

Setting up a conda environment for a new project you just cloned:

```bash
# Clone the project
git clone https://github.com/user/ml-project.git
cd ml-project

# Generate and create conda environment
python /path/to/EnvAgent/main.py .

# Activate and start working
conda activate ml-project
python train.py
```

### Use Case 2: Legacy Project Without environment.yml

You have an old project with no environment file:

```bash
# Generate environment.yml from existing code
python /path/to/EnvAgent/main.py /path/to/legacy/project

# EnvAgent analyzes all .py files and generates environment.yml
# Then automatically creates the conda environment

conda activate legacy_project
```

### Use Case 3: Machine Learning Project with CUDA

Your ML/DL project uses TensorFlow/PyTorch with GPU:

```bash
python /path/to/EnvAgent/main.py ~/tensorflow_project

# EnvAgent automatically detects:
# - TensorFlow/PyTorch version
# - CUDA version requirement
# - cuDNN version requirement
# - Other ML dependencies (numpy, scipy, etc.)

conda activate tensorflow_project
```

### Use Case 4: Review Before Creating

Generate environment.yml but review before creating:

```bash
# Generate environment.yml WITHOUT creating conda environment
python /path/to/EnvAgent/main.py ~/project --no-create

# Review the generated file
cat environment.yml

# Edit if needed
nano environment.yml

# Create manually when satisfied
conda env create -f environment.yml
```

### Use Case 5: Multiple Sub-projects

Monorepo with multiple Python sub-projects:

```bash
# Generate separate environments for each component
python /path/to/EnvAgent/main.py ./backend -n backend-env
python /path/to/EnvAgent/main.py ./api -n api-env
python /path/to/EnvAgent/main.py ./ml_module -n ml-env

# Activate as needed
conda activate backend-env
# or
conda activate ml-env
```

### Use Case 6: Different Python Versions

Project requires specific Python version:

```bash
# Specify Python version
python /path/to/EnvAgent/main.py ~/project --python-version 3.10

# EnvAgent uses Python 3.10 in the environment
conda activate project  # Uses Python 3.10
```

### Use Case 7: Sharing with Team

Create reproducible environment for your team:

```bash
# Generate environment.yml
python /path/to/EnvAgent/main.py . --no-create

# Commit to git
git add environment.yml
git commit -m "Add conda environment specification"
git push

# Team members can then:
# git pull
# conda env create -f environment.yml
# conda activate project_name
```
