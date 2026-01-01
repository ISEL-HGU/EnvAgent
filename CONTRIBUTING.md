# Contributing to EnvAgent

Thank you for your interest in contributing to EnvAgent! This document provides guidelines and information for developers.

## Development Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd EnvAgent

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if any)
pip install pytest black flake8 mypy
```

### 2. Configure Environment

```bash
cp .env.example .env
# Add your OpenAI API key to .env
```

## Project Architecture

### Component Overview

```
EnvAgent/
├── config/          # Configuration management
├── agents/          # AI agents (analyzer & builder)
├── utils/           # Utility modules
└── main.py          # CLI entry point
```

### Key Components

#### 1. LocalReader (`utils/local_reader.py`)
- **Purpose**: Read project files from disk
- **Key Methods**:
  - `read_files()`: Returns dict of filename → content
  - `_find_python_files()`: Recursively finds .py files
- **Extension Points**: Add new file types to `TARGET_FILES`

#### 2. Memory (`utils/memory.py`)
- **Purpose**: Share data between agents
- **Data Fields**:
  - `project_name`: str
  - `package_list`: List[str]
  - `python_version`: str
  - `cuda_version`: Optional[str]
  - `cudnn_version`: Optional[str]
  - `system_dependencies`: List[str]
  - `raw_analysis`: str

#### 3. ProjectAnalyzer (`agents/project_analyzer.py`)
- **Purpose**: Analyze files using GPT-4
- **Key Methods**:
  - `analyze(files_content, memory)`: Populates memory
- **Extension Points**: Modify `ANALYSIS_PROMPT` for better detection

#### 4. EnvironmentBuilder (`agents/env_builder.py`)
- **Purpose**: Generate environment.yml
- **Key Methods**:
  - `build(memory)`: Returns YAML content
  - `save_to_file(content, path)`: Writes to disk
- **Extension Points**: Modify `BUILD_PROMPT` for different formats

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions and classes
- Maximum line length: 100 characters

```python
def example_function(param: str) -> Dict[str, str]:
    """
    Brief description.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    pass
```

### Running Code Quality Tools

```bash
# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

### Testing

```bash
# Run tests (when available)
pytest

# Run specific test
pytest tests/test_local_reader.py

# With coverage
pytest --cov=. --cov-report=html
```

## Adding New Features

### Example: Adding Support for New File Types

1. **Update LocalReader**:
```python
# In utils/local_reader.py
TARGET_FILES = [
    "README.md",
    "requirements.txt",
    "setup.py",
    "pyproject.toml",
    "Pipfile",  # Add new file type
]
```

2. **Update Analyzer Prompt**:
```python
# In agents/project_analyzer.py
ANALYSIS_PROMPT = """
...
Also check Pipfile for dependencies
...
"""
```

3. **Test**:
```bash
python main.py test_project_with_pipfile
```

### Example: Supporting Different Output Formats

1. **Create new builder**:
```python
# agents/docker_builder.py
class DockerBuilder:
    def build(self, memory: Memory) -> str:
        """Generate Dockerfile content."""
        pass
```

2. **Update main.py**:
```python
# Add --format argument
parser.add_argument(
    "-f", "--format",
    choices=["conda", "docker"],
    default="conda"
)
```

## Debugging

### Enable Verbose Logging

```python
# In main.py
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

### Test Individual Components

```python
# Test LocalReader
from utils import LocalReader
reader = LocalReader("./test_example_project")
files = reader.read_files()
print(f"Found {len(files)} files")

# Test Memory
from utils import Memory
mem = Memory()
mem.project_name = "test"
print(mem)
```

### Mock OpenAI API for Testing

```python
# For testing without API calls
class MockAnalyzer:
    def analyze(self, files_content, memory):
        memory.project_name = "test_project"
        memory.python_version = "3.9"
        memory.package_list = ["numpy==1.24.0"]
```

## Common Issues and Solutions

### Import Errors

**Problem**: `ModuleNotFoundError` when running locally

**Solution**: Run from project root:
```bash
cd EnvAgent
python main.py .
```

### OpenAI API Errors

**Problem**: Rate limits or API errors

**Solution**: Add retry logic or use different model:
```python
# In project_analyzer.py
model="gpt-4-turbo-preview",  # Change to gpt-3.5-turbo for testing
```

## Pull Request Process

1. **Fork the repository**

2. **Create a feature branch**:
```bash
git checkout -b feature/my-new-feature
```

3. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

4. **Commit with clear messages**:
```bash
git commit -m "Add support for Pipfile parsing"
```

5. **Push and create PR**:
```bash
git push origin feature/my-new-feature
```

6. **PR Checklist**:
   - [ ] Code follows style guidelines
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] No breaking changes (or documented)

## Release Process

1. Update version in `__version__.py` (if exists)
2. Update CHANGELOG.md
3. Create git tag
4. Push to repository

## Getting Help

- Open an issue for bugs
- Start a discussion for feature ideas
- Ask questions in discussions

## Code of Conduct

- Be respectful
- Provide constructive feedback
- Help others learn

## Future Enhancements

Ideas for contributors:

1. **Testing Framework**
   - Add pytest tests
   - Add integration tests
   - Mock OpenAI responses

2. **Additional Output Formats**
   - Docker support
   - requirements.txt generation
   - poetry support

3. **Improved Detection**
   - Better version detection
   - System package detection
   - OS-specific dependencies

4. **CLI Improvements**
   - Progress bars
   - Interactive mode
   - Config file support

5. **Performance**
   - Caching
   - Parallel file reading
   - Streaming responses

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
