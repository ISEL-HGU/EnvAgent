"""
Environment Fixer Agent.
Uses OpenAI GPT-4 to fix conda environment errors.
"""

import logging
import re
from openai import OpenAI

from config.settings import settings
from utils.memory import Memory

logger = logging.getLogger(__name__)


class EnvironmentFixer:
    """Fixes conda environment errors using AI."""

    # -------------------------------------------------------------------------
    # 🧠 INTELLIGENT AGENT PROMPT (Context-Aware Inference)
    # -------------------------------------------------------------------------
    FIX_PROMPT = """You are an expert DevOps Engineer specializing in Python environments.
A conda environment creation FAILED.
Your goal is to fix the `environment.yml` not just by reacting to errors, but by **INFERRING the correct project context**.

## 📄 CURRENT environment.yml:
{current_yml}

## ❌ ERROR LOG:
{error_message}

## 📜 FIX HISTORY:
{error_history}

## 🧠 INTELLIGENT REASONING STRATEGY:

### 1. 🕵️‍♂️ INFER PYTHON VERSION (The most critical step)
- **Problem:** If build errors occur (`gcc`, `Python.h`, `wheel`, `Py_UNICODE`), the Python version is likely incompatible.
- **Your Job:** Look at the other libraries in the list to **GUESS** the right Python version.
  - Case A: Modern Data Science (`pandas`, `scipy`, `spacy`) → **PIN `python=3.10`** (Best compatibility).
  - Case B: Very Old Legacy (`tensorflow<2.0`, `sklearn` old names) → **PIN `python=3.7` or `3.8`**.
  - Case C: Bleeding Edge (`langchain`, `fastapi`) → **PIN `python=3.11`**.
  - **ACTION:** Change `- python` (unpinned) to `- python=3.X` based on your inference.

### 2. 🧩 RESOLVE CONFLICTS (UnsatisfiableError)
- **Problem:** Specific versions (`numpy==1.21.0`) conflict with dependencies.
- **Your Job:** Identify the conflicting package and **RELAX** the constraint.
  - Action: Change `numpy==1.21.0` → `numpy` (Let the solver choose).
  - Action: Change `transformers>=4.0` → `transformers`.

### 3. 📦 PACKAGES NOT FOUND
- **Problem:** Package is not in Conda channels.
- **Your Job:** Move it to the `pip:` section.
  - Action: Remove from main dependencies, add under `- pip:`.

### 4. 🚑 EMERGENCY FIX (If Pip Subprocess Failed)
- **Problem:** Pip failed to build a wheel (e.g., `thinc`, `dlib`).
- **Your Job:** This is almost always a Python version mismatch or missing system headers.
- **Action:** **Revert to Strategy 1** and ensure Python is pinned to a stable version (3.10 is the safest bet for most pip failures).

## 📝 OUTPUT RULES:
1. Return **ONLY** the fixed YAML content.
2. NO Markdown code blocks (```).
3. NO Explanations or Comments.
"""

    def __init__(self):
        """Initialize the EnvironmentFixer with OpenAI client."""
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentFixer initialized")

    def fix(self, current_yml: str, error_message: str, memory: Memory) -> str:
        """
        Generate a fixed environment.yml based on the error.
        """
        logger.info("=" * 70)
        logger.info("🔧 FIXER AGENT STARTING DIAGNOSIS...")
        logger.info("=" * 70)

        # 1. Prepare History Context
        error_history_text = "None - this is the first attempt"
        if memory.error_history:
            history_lines = []
            for i, (err, fix_desc) in enumerate(memory.error_history, 1):
                history_lines.append(f"[Attempt {i}] Fix: {fix_desc}")
                # Keep error brief to save context window
                history_lines.append(f"[Attempt {i}] Error Snippet: {err[:300]}...") 
            error_history_text = "\n".join(history_lines)

        # 2. Build Prompt
        prompt = self.FIX_PROMPT.format(
            current_yml=current_yml,
            error_message=error_message,
            error_history=error_history_text
        )

        try:
            logger.info("🤖 AI is analyzing dependencies to infer the best environment configuration...")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Python Dependency Expert. If you see build errors, your priority is to PIN Python to a stable version (usually 3.10) to fix ABI compatibility."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3, # Slightly creative for inference, but stable for code
            )

            fixed_yml = response.choices[0].message.content.strip()
            fixed_yml = self._clean_markdown(fixed_yml)

            # 3. Validation: Did AI actually do anything?
            if self._are_yamls_identical(current_yml, fixed_yml):
                logger.warning("⚠️  AI suggested no changes. Engaging Rule-Based Fallback Protocol...")
                fixed_yml = self._heuristic_fallback(current_yml, error_message)

            return fixed_yml

        except Exception as e:
            logger.error(f"❌ AI Inference Failed: {e}")
            logger.info("Engaging Rule-Based Fallback Protocol...")
            return self._heuristic_fallback(current_yml, error_message)

    def _clean_markdown(self, text: str) -> str:
        """Remove ```yaml wrappers."""
        if "```" in text:
            lines = text.split("\n")
            # Filter out lines that are just ``` or ```yaml
            lines = [l for l in lines if not l.strip().startswith("```")]
            return "\n".join(lines).strip()
        return text

    def _are_yamls_identical(self, yml1: str, yml2: str) -> bool:
        """Compare normalized YAMLs."""
        def normalize(yml):
            lines = [line.strip() for line in yml.strip().split("\n") if line.strip() and not line.strip().startswith("#")]
            return "\n".join(sorted(lines))
        return normalize(yml1) == normalize(yml2)

    def _heuristic_fallback(self, yml: str, error: str) -> str:
        """
        Rule-Based Fallback: When AI fails, apply hard rules.
        """
        logger.info("🔧 [FALLBACK] Applying Safety Net Rules...")
        
        lines = yml.split('\n')
        fixed_lines = []
        
        # Rule 1: Detect C/C++ Build Errors -> Force Python 3.10
        is_build_error = any(x in error for x in [
            "gcc", "g++", "Python.h", "build", "wheel", "Py_UNICODE", "_PyInterpreterState"
        ])
        
        python_processed = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check if python line
            if stripped.startswith("- python"):
                # If we have a build error and python is unpinned or weird, force 3.10
                if is_build_error:
                    logger.info("💡 [FALLBACK] Build error detected. Forcing 'python=3.10'")
                    indent = line[:line.find("-")]
                    fixed_lines.append(f"{indent}- python=3.10")
                else:
                    fixed_lines.append(line)
                python_processed = True
                continue
            
            # Rule 2: Strip versions for explicitly conflicting packages
            # Regex to find package name in error like "conflict with 'numpy'" or "'numpy' not found"
            pkg_match = re.search(r'["\']([a-zA-Z0-9_-]+)(?:==|>=|<=)', error)
            target_pkg = pkg_match.group(1) if pkg_match else None
            
            should_strip = False
            if target_pkg and target_pkg in stripped and ("=" in stripped or ">" in stripped):
                should_strip = True
                
            if should_strip:
                pkg_name = stripped.replace("-", "").strip().split("=")[0].split(">")[0].split("<")[0]
                indent = line[:line.find("-")]
                fixed_lines.append(f"{indent}- {pkg_name}")
                logger.info(f"💡 [FALLBACK] Removing constraints from '{pkg_name}'")
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def extract_fix_summary(self, original_yml: str, fixed_yml: str) -> str:
        original_lines = set(original_yml.strip().split("\n"))
        fixed_lines = set(fixed_yml.strip().split("\n"))
        
        # Find lines that contain 'python=' to see if version changed
        py_ver_change = any("python=" in line for line in (fixed_lines - original_lines))
        if py_ver_change:
            return "Pinned/Changed Python Version (Inferred Stability)"
            
        added = fixed_lines - original_lines
        if added:
            added_list = [line.strip() for line in added if line.strip()]
            return f"Updated: {', '.join(added_list[:2])}..."
            
        return "Relaxed constraints"