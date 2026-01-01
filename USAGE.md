# EnvAgent Usage Guide

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
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Run EnvAgent

```bash
# Analyze current directory
python main.py .

# Analyze specific project
python main.py /path/to/your/project

# Specify output file
python main.py /path/to/your/project -o my_environment.yml
```

## Detailed Usage

### Command Line Options

```
python main.py [-h] [-o OUTPUT] directory

Positional arguments:
  directory             Path to the project directory to analyze

Optional arguments:
  -h, --help           Show help message and exit
  -o OUTPUT, --output OUTPUT
                       Output file path (default: ./environment.yml)
```

### What Files Are Analyzed?

EnvAgent reads and analyzes:

1. **Configuration files**:
   - `requirements.txt`
   - `setup.py`
   - `pyproject.toml`
   - `README.md`

2. **All Python files** (`.py`) in the directory, excluding:
   - `__pycache__`
   - `.git`
   - `venv` / `env` / `ENV`
   - `node_modules`
   - `.pytest_cache`
   - Build directories

### Example Workflow

```bash
# 1. Analyze your ML project
python main.py ~/my_ml_project

# Output:
# ============================================================
# EnvAgent - Conda Environment Generator
# ============================================================
#
# 📁 Project directory: /home/user/my_ml_project
#
# 📖 Step 1/3: Reading project files...
#    Found 15 files to analyze
#
# 🔍 Step 2/3: Analyzing project dependencies...
#    (This may take a moment...)
#    ✓ Project: my_ml_project
#    ✓ Python version: 3.9
#    ✓ Packages found: 12
#    ✓ CUDA version: 11.8
#    ✓ cuDNN version: 8.6
#
# 🔨 Step 3/3: Generating environment.yml...
#    ✓ Saved to: /home/user/environment.yml
#
# ============================================================
# ✅ Success! Environment file generated.
# ============================================================

# 2. Review the generated file
cat environment.yml

# 3. Create the Conda environment
conda env create -f environment.yml

# 4. Activate the environment
conda activate my_ml_project
```

## Testing with Example Project

A test project is included in `test_example_project/`:

```bash
# Test with the example project
python main.py test_example_project -o test_output.yml

# Check the result
cat test_output.yml
```

Expected output structure:
```yaml
name: ml_test_project
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
```

## Understanding the Output

### Environment File Structure

```yaml
name: project_name           # Detected from directory/files
channels:
  - conda-forge              # Primary channel
  - defaults                 # Fallback channel
dependencies:
  - python=3.9               # Detected Python version
  - cudatoolkit=11.8         # Only if ML/DL project
  - cudnn=8.6                # Only if needed
  - pip                      # Pip package manager
  - pip:                     # Python packages
    - package1==1.0.0        # With specific versions
    - package2>=2.0.0        # Or version constraints
```

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

## Common Use Cases

### Case 1: Legacy Project

You have an old project without a proper environment file:
```bash
python main.py /path/to/legacy/project
# Review and adjust versions in generated file
conda env create -f environment.yml
```

### Case 2: Machine Learning Project

Your ML project needs CUDA:
```bash
python main.py /path/to/ml/project
# EnvAgent automatically detects CUDA/cuDNN requirements
```

### Case 3: Multiple Sub-projects

Analyze each sub-project separately:
```bash
python main.py ./backend -o backend_env.yml
python main.py ./frontend -o frontend_env.yml
python main.py ./ml_module -o ml_env.yml
```
