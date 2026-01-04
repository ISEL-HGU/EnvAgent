# EnvAgent

Automatic Conda environment.yml generator that analyzes Python projects using AI-powered dependency analysis with **automatic error fixing**.

Stop manually managing conda environments! EnvAgent automatically scans your Python project, detects all dependencies, and creates a working conda environment with automatic error fixing.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your OpenAI API key
cp .env.example .env
# Edit .env and add your API key

# 3. Run EnvAgent on your project
python main.py /path/to/your/project

# 4. Your conda environment is ready!
conda activate your_project_name
```

**That's it!** EnvAgent handles everything automatically.

---

## Features

- 🔍 **Smart Analysis** - Scans Python files, requirements.txt, setup.py, and more
- 🤖 **AI-Powered** - Uses GPT-4 to intelligently detect dependencies and versions
- 📦 **Conda Ready** - Generates valid environment.yml files
- 🎯 **ML/DL Support** - Automatically detects CUDA/cuDNN requirements
- 🔄 **Auto-Fix** - Fixes conda errors automatically (up to 8 retry attempts)
- 🛠️ **Error Recovery** - AI diagnoses and resolves dependency conflicts
- 🚀 **One Command** - Simple CLI interface

## How It Works

EnvAgent v2.0 uses a **token-efficient architecture** that processes your project in 6 steps:

1. **System Check** - Verifies conda and required tools are installed
2. **Decision Agent** - Checks if environment files already exist
3. **File Filter** - Finds relevant Python and config files (no LLM)
4. **Code Scanner** - Analyzes files one-by-one to detect dependencies
5. **Environment Builder** - Generates environment.yml from analysis
6. **Auto-Fix Loop** - Creates conda environment with automatic error fixing (up to 8 retries)

![EnvAgent Architecture](architecture.png)

### Token-Efficient Design

EnvAgent v2.0 processes files **one-by-one** instead of sending everything at once, avoiding token limits and reducing API costs.

## Installation

### Prerequisites

- Python 3.8 or higher
- Conda (Anaconda or Miniconda)
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Setup Steps

```bash
# 1. Navigate to EnvAgent directory
cd EnvAgent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create .env file from template
cp .env.example .env

# 4. Edit .env and add your API key
# Replace "API KEY" with your actual OpenAI API key
nano .env   # or use your favorite editor
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

**That's it!** You're ready to use EnvAgent.

## Usage

### Basic Usage

```bash
# Analyze current directory and create conda environment
python main.py .

# Analyze specific project directory
python main.py /path/to/your/project

# Specify custom output location for environment.yml
python main.py /path/to/project custom_env.yml

# Specify custom environment name
python main.py /path/to/project -n my_custom_env_name

# Specify Python version (default: 3.9)
python main.py /path/to/project --python-version 3.10
```

### Advanced Options

```bash
# Generate environment.yml WITHOUT creating conda environment
python main.py /path/to/project --no-create

# Output to subdirectory (auto-creates directory)
python main.py /path/to/project output/env.yml

# Combine options
python main.py ~/my_ml_project my_env.yml -n ml_project --python-version 3.9
```

### Command Line Arguments

```
python main.py <source> [destination] [options]

Arguments:
  source                    Source directory to analyze (required)
  destination              Output path for environment.yml (default: ./environment.yml)

Options:
  -n, --env-name NAME      Custom environment name (default: project directory name)
  --python-version VERSION Python version to use (default: 3.9)
  --no-create             Generate yml only, skip conda environment creation
  -h, --help              Show help message
```

### Complete Example

```bash
# Analyze ML project and create environment
python main.py ~/my_ml_project

# EnvAgent will:
# ✓ Check system requirements
# ✓ Analyze all Python files
# ✓ Detect dependencies (numpy, pandas, tensorflow, etc.)
# ✓ Generate environment.yml
# ✓ Create conda environment automatically
# ✓ Fix any errors that occur

# Activate your new environment
conda activate my_ml_project

# Start coding!
python your_script.py
```

## What Gets Analyzed?

EnvAgent scans your project for:

### Configuration Files
- `requirements.txt` - Python package requirements
- `setup.py` - Package installation scripts
- `pyproject.toml` - Modern Python project configs
- `README.md` - Project documentation

### Source Code
- All `.py` files in your project
- **Excludes**: `venv/`, `__pycache__/`, `.git/`, `node_modules/`, build directories

### What It Detects
- Python package dependencies (numpy, pandas, tensorflow, etc.)
- Package versions and version constraints
- Python version requirements
- CUDA/cuDNN requirements (for ML/DL projects)
- System-level dependencies

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

## Troubleshooting

### "OPENAI_API_KEY not found"

Make sure you've created a `.env` file with your API key:
```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here
```

### "Directory does not exist"

Check your path is correct:
```bash
# Use absolute path
python main.py /full/path/to/project

# Or relative path from current directory
python main.py ../my_project
```

### "conda: command not found"

Install Conda:
- Anaconda: https://www.anaconda.com/download
- Miniconda (lighter): https://docs.conda.io/en/latest/miniconda.html

### Environment creation fails after 8 retries

If automatic fixing fails:
1. Check the generated `environment.yml` file
2. Look for incompatible version constraints
3. Try creating manually: `conda env create -f environment.yml`
4. Review error messages for hints

### API rate limits

If you hit OpenAI rate limits:
- Wait a few minutes and try again
- Check your API usage: https://platform.openai.com/usage
- Consider upgrading your API tier

## Project Structure

```
EnvAgent/
├── agents/                    # AI agents
│   ├── decision_agent.py     # Decides if analysis is needed
│   ├── code_scanner.py       # Scans files one-by-one
│   ├── env_builder.py        # Generates environment.yml
│   └── env_fixer.py          # Fixes conda errors
├── config/
│   └── settings.py           # Configuration (API keys, MAX_RETRIES=8)
├── utils/                    # Utility functions
│   ├── file_filter.py        # Filters relevant files
│   ├── conda_executor.py     # Executes conda commands
│   ├── system_checker.py     # Checks system requirements
│   └── helpers.py            # Helper functions
├── main.py                   # CLI entry point
├── requirements.txt          # Python dependencies
├── .env.example             # Template for API keys
└── README.md                # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Documentation

- [README.md](README.md) - Main documentation (this file)
- [QUICKSTART.md](QUICKSTART.md) - 5-minute quick start guide
- [USAGE.md](USAGE.md) - Detailed usage examples
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details

## License

MIT License

## Support

- GitHub Issues: Report bugs and request features
- Documentation: Check the docs listed above
- OpenAI API Help: https://platform.openai.com/docs
