# EnvAgent Quick Start Guide

Get your conda environment up and running in **5 minutes**!

## Prerequisites

Before you start, make sure you have:
- **Python 3.8+** installed
- **Conda** installed (Anaconda or Miniconda)
- **OpenAI API key** ([Get one here](https://platform.openai.com/api-keys))

---

## Step 1: Install Dependencies (1 min)

```bash
cd EnvAgent
pip install -r requirements.txt
```

This installs:
- `openai>=1.0.0` - For GPT-4 API access
- `python-dotenv>=1.0.0` - For environment variable management

---

## Step 2: Configure API Key (1 min)

```bash
# Copy the example file
cp .env.example .env

# Edit and add your OpenAI API key
nano .env  # or use: vim, code, etc.
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

**Where to get your API key:** https://platform.openai.com/api-keys

---

## Step 3: Run Your First Analysis (3 min)

```bash
# Analyze your project (replace with your actual project path)
python main.py /path/to/your/project

# Or analyze current directory
python main.py .

# Or specify custom output location
python main.py /path/to/project output/env.yml
```

---

## What You'll See

EnvAgent v2.0 runs through 6 steps automatically:

```
============================================================
EnvAgent - Conda Environment Generator v2.0
Token-Efficient Architecture
============================================================

📁 Project directory: /path/to/your/project
📄 Output file: ./environment.yml

🔍 Step 0/6: Checking system requirements...
   ✓ All system checks passed

📋 Step 1/6: Analyzing project structure...
   Decision: No existing environment found, will proceed
   ✓ Will proceed with dependency analysis

📁 Step 2/6: Filtering relevant source files...
   ✓ Found 25 relevant files
     - Dependency files: 2
     - Python source files: 23

🔬 Step 3/6: Scanning source files for dependencies...
   (This processes files one-by-one to avoid token limits)
   ✓ Dependency summary saved to: dependency_summary.txt

🔨 Step 4/6: Generating environment.yml...
   ✓ Saved to: ./environment.yml

🚀 Step 5/6: Creating conda environment 'your_project'...
   (Maximum 8 attempts with auto-fix)
   [Attempt 1/8]

============================================================
✅ SUCCESS! Environment created successfully.
============================================================

Environment details:
  • Name: your_project
  • Config file: ./environment.yml
  • Summary file: dependency_summary.txt

Next steps:
  1. Activate the environment:
     conda activate your_project

  2. Verify installation:
     python --version

  3. Deactivate when done:
     conda deactivate
```

---

## Step 4: Activate and Use Your Environment

```bash
# Activate the conda environment (name will match your project)
conda activate your_project

# Verify it works
python --version
python -c "import numpy, pandas; print('Success!')"

# Start working on your project
python your_script.py

# When done, deactivate
conda deactivate
```

---

## Common Issues & Quick Fixes

### "OPENAI_API_KEY not found"
**Fix**: Make sure you created `.env` and added your API key
```bash
cp .env.example .env
nano .env  # Add your API key
```

### "Directory does not exist"
**Fix**: Check your path is correct
```bash
# Use absolute path
python main.py /Users/you/projects/my_project

# Or relative path
python main.py ../my_project
```

### "No module named 'openai'"
**Fix**: Install dependencies
```bash
pip install -r requirements.txt
```

### "conda: command not found"
**Fix**: Install conda first
- Download Anaconda: https://www.anaconda.com/download
- Or Miniconda: https://docs.conda.io/en/latest/miniconda.html

---

## Advanced Options

### Skip Conda Environment Creation

Generate `environment.yml` **without** creating the conda environment:

```bash
python main.py /path/to/project --no-create
```

Then create it manually later:
```bash
conda env create -f environment.yml
conda activate project_name
```

### Custom Environment Name

```bash
python main.py /path/to/project -n my_custom_name
# Creates environment named 'my_custom_name'
```

### Custom Python Version

```bash
python main.py /path/to/project --python-version 3.10
# Uses Python 3.10 instead of default 3.9
```

### Combine All Options

```bash
python main.py ~/ml_project output/env.yml -n ml_env --python-version 3.10 --no-create
```

---

## Real-World Examples

### Machine Learning Project
```bash
python main.py ~/tensorflow_project
# Auto-detects: TensorFlow, CUDA, cuDNN, NumPy, etc.
conda activate tensorflow_project
```

### Data Science Project
```bash
python main.py ~/data_analysis
# Auto-detects: pandas, numpy, matplotlib, scikit-learn
conda activate data_analysis
```

### Web Application
```bash
python main.py ~/flask_app
# Auto-detects: Flask, SQLAlchemy, requests, etc.
conda activate flask_app
```

---

## What's Next?

**Read More Documentation:**
- [README.md](README.md) - Full documentation
- [USAGE.md](USAGE.md) - Detailed usage examples
- [ARCHITECTURE.md](ARCHITECTURE.md) - How EnvAgent works internally

**Get Help:**
```bash
python main.py --help
```

**Check API Usage:**
- OpenAI Dashboard: https://platform.openai.com/usage
- Monitor your API costs and rate limits

---

## That's It!

You're now ready to use EnvAgent!

**Happy environment building!** 🚀

---

## Need Help?

- **Documentation**: Check the docs above
- **Issues**: Open an issue on GitHub
- **API Problems**: https://platform.openai.com/docs
