# EnvAgent Quick Start Guide

Get up and running with EnvAgent in 3 minutes!

## Step 1: Install Dependencies (1 min)

```bash
cd EnvAgent
pip install -r requirements.txt
```

This installs:
- `openai` - For GPT-4 API access
- `python-dotenv` - For environment variable management

## Step 2: Configure API Key (1 min)

```bash
# Copy the example file
cp .env.example .env

# Edit and add your OpenAI API key
nano .env  # or use your preferred editor
```

Your `.env` should look like:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

Get your API key from: https://platform.openai.com/api-keys

## Step 3: Run Your First Analysis (1 min)

```bash
# Test with the included example project (output to ./environment.yml)
python main.py test_example_project

# Specify custom output location
python main.py test_example_project test_env.yml

# Or analyze your own project
python main.py /path/to/your/project

# Or analyze current directory
python main.py .
```

## What You'll See

```
============================================================
EnvAgent - Conda Environment Generator
============================================================

📁 Project directory: /home/user/test_example_project

📖 Step 1/3: Reading project files...
   Found 3 files to analyze

🔍 Step 2/3: Analyzing project dependencies...
   (This may take a moment...)
   ✓ Project: ml_test_project
   ✓ Python version: 3.9
   ✓ Packages found: 4
   ✓ CUDA version: 11.8
   ✓ cuDNN version: 8.6

🔨 Step 3/3: Generating environment.yml...
   ✓ Saved to: /home/user/EnvAgent/environment.yml

============================================================
✅ Success! Environment file generated.
============================================================

Next steps:
1. Review the generated file: /home/user/EnvAgent/environment.yml
2. Create the environment: conda env create -f environment.yml
3. Activate the environment: conda activate ml_test_project
```

## Step 4: Use the Generated Environment

```bash
# Review the generated file
cat environment.yml

# Create the conda environment
conda env create -f environment.yml

# Activate it
conda activate ml_test_project  # or whatever your project name is

# Verify it works
python -c "import numpy, pandas; print('Success!')"
```

## Common First-Time Issues

### Issue: "OPENAI_API_KEY not found"
**Fix**: Make sure you created `.env` and added your API key

### Issue: "Directory does not exist"
**Fix**: Check your path is correct:
```bash
# Use full path
python main.py /home/user/my_project

# Or relative
python main.py ../my_project
```

### Issue: "No module named 'openai'"
**Fix**: Install dependencies:
```bash
pip install -r requirements.txt
```

## What's Next?

1. **Read the full documentation**: [README.md](README.md)
2. **Learn advanced usage**: [USAGE.md](USAGE.md)
3. **Contribute**: [CONTRIBUTING.md](CONTRIBUTING.md)

## Example: Analyze a Real Project

```bash
# Example with a TensorFlow project
python main.py ~/my_tensorflow_project tf_env.yml

# Example with a data science project
python main.py ~/my_data_analysis analysis_env.yml

# Example with current directory
python main.py . environment.yml

# Output to subdirectory (creates if needed)
python main.py ~/my_project outputs/env.yml
```

## Troubleshooting

**OpenAI API Rate Limits?**
- Wait a few minutes and try again
- Check your API usage at: https://platform.openai.com/usage

**Generated file looks wrong?**
- It's AI-generated, so always review before using
- You can manually edit the `environment.yml` file
- Re-run with better structured source files (add requirements.txt)

**Want to improve detection?**
- Add a `requirements.txt` to your project
- Include version info in imports comments
- Add a README with dependency information

## Quick Reference

```bash
# Basic usage
python main.py <directory>

# Custom output
python main.py <directory> -o custom_name.yml

# Help
python main.py --help

# Analyze multiple projects
python main.py project1 -o env1.yml
python main.py project2 -o env2.yml
```

## That's It!

You're now ready to use EnvAgent. Happy environment building! 🚀

---

**Need Help?**
- Check [USAGE.md](USAGE.md) for detailed usage
- See [README.md](README.md) for full documentation
- Open an issue on GitHub for bugs
