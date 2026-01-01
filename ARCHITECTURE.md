# EnvAgent Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          EnvAgent v2.0                          │
│              AI-Powered Conda Environment Generator              │
│                    with Auto-Fix Capabilities                    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                 │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  main.py                                                     │     │
│  │  • Argument parsing (directory, --output, --env-name, etc.) │     │
│  │  • Orchestrates the 4-step workflow                         │     │
│  │  • Implements retry loop with MAX_RETRIES=5                 │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌───────────────────────────────────────────────────────────────────────┐
│                           Config Layer                                 │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  config/settings.py                                          │     │
│  │  • Loads OPENAI_API_KEY from .env                           │     │
│  │  • MAX_RETRIES = 5 (strict limit)                           │     │
│  │  • Global settings instance                                  │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌───────────────────────────────────────────────────────────────────────┐
│                          Utilities Layer                               │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ LocalReader      │  │   Memory     │  │  CondaExecutor     │     │
│  │                  │  │              │  │                    │     │
│  │ • Read files     │  │ • Project    │  │ • create_env()     │     │
│  │ • .py, .txt, md  │  │   metadata   │  │ • remove_env()     │     │
│  │ • Recursive      │  │ • Packages   │  │ • check_exists()   │     │
│  │ • Exclude venv   │  │ • Versions   │  │ • Subprocess calls │     │
│  │                  │  │ • Error hist │  │ • Timeout handling │     │
│  └──────────────────┘  └──────────────┘  └────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌───────────────────────────────────────────────────────────────────────┐
│                            Agents Layer                                │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ ProjectAnalyzer  │  │ EnvBuilder   │  │  EnvironmentFixer  │     │
│  │                  │  │              │  │                    │     │
│  │ • GPT-4 API      │  │ • GPT-4 API  │  │ • GPT-4 API        │     │
│  │ • Analyze files  │  │ • Generate   │  │ • Diagnose errors  │     │
│  │ • Extract deps   │  │   YAML       │  │ • Generate fixes   │     │
│  │ • Detect CUDA    │  │ • Channels   │  │ • Track history    │     │
│  │ • Find versions  │  │ • Format     │  │ • Smart retry      │     │
│  └──────────────────┘  └──────────────┘  └────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Step 1: File Reading

```
Project Directory
      │
      ↓
┌─────────────┐
│ LocalReader │
└─────────────┘
      │
      ↓
files_content: Dict[str, str]
{
  "README.md": "...",
  "requirements.txt": "...",
  "src/main.py": "...",
  ...
}
```

### Step 2: Analysis

```
files_content
      │
      ↓
┌──────────────────┐
│ ProjectAnalyzer  │ ──→ OpenAI GPT-4 API
└──────────────────┘
      │
      ↓
Memory object populated:
{
  project_name: "my_project",
  python_version: "3.9",
  package_list: ["numpy==1.24.0", ...],
  cuda_version: "11.8",
  error_history: []
}
```

### Step 3: Environment Generation

```
Memory
      │
      ↓
┌──────────────┐
│ EnvBuilder   │ ──→ OpenAI GPT-4 API
└──────────────┘
      │
      ↓
environment.yml content:
name: my_project
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - pip
  - pip:
    - numpy==1.24.0
```

### Step 4: Auto-Fix Loop (NEW!)

```
environment.yml
      │
      ↓
┌─────────────────────────────────────────────────────────┐
│                   Retry Loop (MAX 5)                    │
│                                                          │
│  Attempt 1:                                              │
│    ┌──────────────────┐                                 │
│    │ CondaExecutor    │ conda env create -f yml         │
│    └──────────────────┘                                 │
│           │                                              │
│           ├─→ SUCCESS? ──→ DONE!                        │
│           │                                              │
│           └─→ FAILED                                     │
│                 │                                        │
│                 ↓                                        │
│           ┌──────────────────┐                          │
│           │ EnvironmentFixer │ ──→ GPT-4: Analyze error │
│           └──────────────────┘                          │
│                 │                                        │
│                 ↓                                        │
│           Fixed environment.yml                          │
│                 │                                        │
│                 ↓                                        │
│  Attempt 2: (repeat with fixed yml)                     │
│    ...                                                   │
│                                                          │
│  Attempt 5: Last chance                                 │
│    SUCCESS? ──→ DONE!                                   │
│    FAILED? ──→ GIVE UP                                  │
└─────────────────────────────────────────────────────────┘
```

## Error History Tracking

```
Attempt 1: PackagesNotFoundError: invalid-pkg
           ↓
        ┌────────────────────────────────┐
        │ Memory.error_history.append()  │
        │ ("PackagesNotFoundError...",   │
        │  "Removed invalid package")    │
        └────────────────────────────────┘
           ↓
Attempt 2: VersionConflict: pkg1 vs pkg2
           ↓
        ┌────────────────────────────────┐
        │ Memory.error_history.append()  │
        │ ("VersionConflict...",         │
        │  "Loosened constraints")       │
        └────────────────────────────────┘
           ↓
        Error history sent to GPT-4 for context
```

## Module Dependencies

```
main.py
  ├─→ config.settings (MAX_RETRIES, api_key)
  ├─→ utils.LocalReader
  ├─→ utils.Memory
  ├─→ utils.CondaExecutor
  ├─→ agents.ProjectAnalyzer
  ├─→ agents.EnvironmentBuilder
  └─→ agents.EnvironmentFixer

agents/project_analyzer.py
  ├─→ openai (OpenAI client)
  ├─→ config.settings (api_key)
  └─→ utils.Memory

agents/env_builder.py
  ├─→ openai (OpenAI client)
  ├─→ config.settings (api_key)
  └─→ utils.Memory

agents/env_fixer.py
  ├─→ openai (OpenAI client)
  ├─→ config.settings (api_key)
  └─→ utils.Memory

utils/conda_executor.py
  └─→ subprocess

utils/local_reader.py
  └─→ pathlib, os

utils/memory.py
  └─→ dataclasses

config/settings.py
  └─→ dotenv
```

## API Call Flow

```
User runs: python main.py /path/to/project

API Call 1: ProjectAnalyzer
  ↓
Prompt: "Analyze these files and extract dependencies..."
Files: README, requirements.txt, *.py
  ↓
Response: JSON with packages, versions, CUDA, etc.

API Call 2: EnvironmentBuilder
  ↓
Prompt: "Generate environment.yml with these specs..."
Input: Memory (packages, versions, etc.)
  ↓
Response: Valid YAML content

[If conda create fails]

API Call 3: EnvironmentFixer (Attempt 1)
  ↓
Prompt: "Fix this error: PackagesNotFoundError..."
Input: Current yml + error message + history
  ↓
Response: Fixed YAML content

[If still fails]

API Call 4: EnvironmentFixer (Attempt 2)
  ↓
[... up to 5 attempts total ...]
```

## File System Interactions

```
Input:
  /path/to/project/
    ├── README.md           (read)
    ├── requirements.txt    (read)
    ├── setup.py            (read)
    ├── pyproject.toml      (read)
    └── src/
        ├── main.py         (read)
        └── utils.py        (read)

Output:
  ./environment.yml         (write, overwrite on each retry)

Conda:
  ~/.conda/envs/
    └── my_project/         (create or fail)
```

## State Machine

```
┌──────────┐
│  START   │
└──────────┘
     │
     ↓
┌──────────────┐
│ Read Files   │
└──────────────┘
     │
     ↓
┌──────────────┐
│   Analyze    │
└──────────────┘
     │
     ↓
┌──────────────┐
│  Generate    │
└──────────────┘
     │
     ↓
   ┌─────────────────┐
   │ --no-create?    │
   └─────────────────┘
     │              │
   YES             NO
     │              │
     ↓              ↓
┌────────┐   ┌──────────────┐
│  DONE  │   │ Attempt 1    │
└────────┘   └──────────────┘
                    │
                    ↓
              ┌───────────┐
              │ Success?  │
              └───────────┘
               │         │
              YES       NO
               │         │
               ↓         ↓
          ┌────────┐  ┌──────────┐
          │  DONE  │  │ Attempt  │
          └────────┘  │  <= 5?   │
                      └──────────┘
                       │        │
                      YES      NO
                       │        │
                       ↓        ↓
                   ┌──────┐  ┌──────┐
                   │ Fix  │  │ FAIL │
                   └──────┘  └──────┘
                       │
                       ↓
                   (retry)
```

## Configuration Flow

```
.env file
  ↓
load_dotenv()
  ↓
os.getenv("OPENAI_API_KEY")
  ↓
Settings class
  ↓
settings.api_key ──→ All agents
settings.MAX_RETRIES ──→ main.py retry loop
```

## Logging Architecture

```
All components log to Python logging:

main.py:
  logger.info("Analyzing project: ...")
  logger.error("Unexpected error: ...")

agents/*:
  logger.info("ProjectAnalyzer initialized")
  logger.error("Error during analysis: ...")

utils/*:
  logger.info("Creating conda environment...")
  logger.warning("Failed to read file...")

Output:
  2025-12-31 10:00:00 - __main__ - INFO - Analyzing project...
  2025-12-31 10:00:15 - agents.project_analyzer - INFO - Analysis complete
```

## Summary

EnvAgent is a **modular, well-architected system** with:

- ✅ Clear separation of concerns
- ✅ Single Responsibility Principle
- ✅ Dependency injection
- ✅ Comprehensive error handling
- ✅ Detailed logging
- ✅ Type safety
- ✅ Retry mechanism with strict limits
- ✅ AI-powered intelligent fixes
