# EnvAgent

Automatic Conda environment.yml generator that analyzes local project directories using AI-powered dependency analysis with **automatic error fixing**.

## Features

- 🔍 Analyzes Python projects to detect dependencies
- 🤖 Uses OpenAI GPT-4 for intelligent package detection
- 📦 Generates valid Conda environment.yml files
- 🎯 Detects CUDA/cuDNN requirements for ML projects
- 🔄 **Automatically fixes conda errors with up to 5 retry attempts**
- 🛠️ **AI-powered error diagnosis and resolution**
- 🚀 Simple CLI interface

## Project Structure

```
EnvAgent/
├── config/
│   └── settings.py          # API keys, MAX_RETRIES=5
├── agents/
│   ├── __init__.py
│   ├── project_analyzer.py   # Analyzes project structure
│   ├── env_builder.py        # Generates environment.yml
│   └── env_fixer.py          # Fixes conda errors (NEW!)
├── utils/
│   ├── __init__.py
│   ├── local_reader.py       # Reads local project files
│   ├── memory.py             # Shared memory with error history
│   └── conda_executor.py     # Executes conda commands (NEW!)
├── main.py                   # CLI entry point with retry logic
├── requirements.txt
├── .env.example              # Template for API keys
└── .gitignore
```

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
cp .env.example .env
```

4. Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Basic usage (with automatic conda environment creation)

```bash
# Analyze current directory, output to ./environment.yml
python main.py .

# Analyze specific directory
python main.py /path/to/project

# Specify output file (2nd positional argument)
python main.py /path/to/project custom_env.yml

# Output to subdirectory (creates directory if needed)
python main.py /path/to/project test/output/env.yml

# Custom environment name
python main.py /path/to/project env.yml -n my_custom_env
```

### Generate only (skip conda creation)

```bash
# Only generate yml file, don't create environment
python main.py /path/to/project --no-create

# With custom output path
python main.py /path/to/project output/env.yml --no-create
```

### Full example

```bash
# Analyze a project and generate environment.yml
python main.py ~/my_ml_project

# Create the Conda environment
conda env create -f environment.yml

# Activate the environment
conda activate my_ml_project
```

## How It Works

1. **Local Reader**: Reads project files including:
   - README.md
   - requirements.txt
   - setup.py
   - pyproject.toml
   - All .py files (excluding venv, __pycache__, etc.)

2. **Project Analyzer**: Uses GPT-4 to analyze files and extract:
   - Python packages with versions
   - Python version requirement
   - CUDA/cuDNN versions (for ML projects)
   - System dependencies

3. **Environment Builder**: Generates a valid environment.yml with:
   - Proper channel configuration (conda-forge, defaults)
   - Python version
   - CUDA toolkit (if needed)
   - All pip dependencies

4. **Auto-Fix Retry Loop** (NEW!):
   - Attempts to create the conda environment
   - If errors occur, uses GPT-4 to diagnose and fix
   - Retries up to 5 times with progressively refined fixes
   - Tracks error history to avoid repeating failed solutions

## Example Output

```yaml
name: my_project
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
```

## Requirements

- Python 3.8+
- OpenAI API key
- Dependencies listed in requirements.txt

## Error Handling

The tool includes comprehensive error handling for:
- Missing API keys
- Invalid directories
- File reading errors
- API failures

## Logging

All operations are logged with timestamps. Check the console output for detailed information about the analysis process.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
