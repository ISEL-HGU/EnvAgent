"""
Environment Builder Agent (Improved).
- Avoids hardcoding python=3.9
- Infers minimum Python version from project / summary signals
- Generates robust environment.yml via LLM
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from openai import OpenAI

from config.settings import settings
from utils.helpers import sanitize_env_name

logger = logging.getLogger(__name__)


class EnvironmentBuilder:
    """Builds a Conda environment.yml file from analysis results."""

    BUILD_FROM_SUMMARY_PROMPT = """
You are a Senior DevOps Engineer.
Your task is to create a robust `environment.yml` file based on the provided dependency summary.

### PROJECT DETAILS
- **Project Name:** {project_name}
- **Python Version (target):** {python_version}
- **CUDA Requirement:** {cuda_version}

### DETECTED DEPENDENCIES (Summary)
{summary_content}

### 🚨 STRICT RULES

1. **PACKAGE VERSION POLICY:**
   - Avoid exact pinning (e.g., `==1.2.3`) unless the summary explicitly requires it.
   - Prefer no version or loose constraints.

2. **PYTHON VERSION POLICY (IMPORTANT):**
   - Keep the provided Python version as the default target.
   - If you must raise it for compatibility (rare), raise only minimally.

3. **CHANNEL PRIORITY:**
   - Always include `conda-forge` and `defaults`.
   - If CUDA/GPU is needed, include `nvidia` FIRST.

4. **PACKAGE MAPPING:**
   - Map import names to correct packages (e.g., `cv2` -> `opencv`, `sklearn` -> `scikit-learn`, `PIL` -> `pillow`).

5. **OUTPUT FORMAT:**
   - Return ONLY raw YAML (no markdown, no explanations).
"""

    # ---- Heuristic triggers for minimum Python versions ----
    # match/case -> 3.10+
    _PY310_PATTERNS = [
        re.compile(r"^\s*match\s+.+:\s*$", re.MULTILINE),
        re.compile(r"^\s*case\s+.+:\s*$", re.MULTILINE),
    ]
    # typing features etc could be extended later (3.11/3.12 triggers)
    # keep conservative to avoid unnecessary raises.

    def __init__(self):
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("EnvironmentBuilder initialized")

    # ----------------------------
    # Public API
    # ----------------------------
    def build_from_summary(
        self,
        summary_path: str,
        project_name: str = "my_project",
        python_version: Optional[str] = None,
        repo_root: Optional[str] = None,
    ) -> str:
        """
        Generate environment.yml content from a dependency summary file.

        Args:
            summary_path: path to dependency_summary_*.txt
            project_name: env/project name
            python_version: optional; if None -> infer
            repo_root: optional repo root path; used to infer python version
        """
        logger.info(f"Building environment.yml from summary: {summary_path}")

        summary_content = self._read_text(summary_path)

        sanitized_name = sanitize_env_name(project_name)
        logger.info(f"Using sanitized environment name: {sanitized_name}")

        # CUDA hint
        cuda_version = self._infer_cuda(summary_content)

        # Python version inference (avoid fixed default 3.9)
        inferred_py = self._infer_python_version(
            summary_content=summary_content,
            repo_root=repo_root
        )

        target_python = self._choose_python_version(python_version, inferred_py)
        logger.info(f"Target Python version selected: {target_python} (user={python_version}, inferred={inferred_py})")

        prompt = self.BUILD_FROM_SUMMARY_PROMPT.format(
            project_name=sanitized_name,
            python_version=target_python,
            cuda_version=cuda_version,
            summary_content=summary_content
        )

        env_content = self._call_llm(prompt)
        env_content = self._clean_markdown(env_content)

        # Safety check: ensure python= is present and matches target_python loosely
        env_content = self._ensure_python_dep(env_content, target_python)

        return env_content

    # ----------------------------
    # Inference helpers
    # ----------------------------
    def _infer_cuda(self, summary_content: str) -> str:
        if "CUDA Required: Yes" in summary_content or "True" in summary_content:
            return "CUDA 11.8 (Auto-detected)"
        return "Not specified"

    def _infer_python_version(self, summary_content: str, repo_root: Optional[str]) -> str:
        """
        Conservative inference:
        - If repo contains match/case -> >=3.10
        - If summary contains a python requirement hint -> use that
        - Else default to a modern safe baseline (3.11)
        """
        # 1) Try extracting explicit hint from summary (if you later add it)
        # Example accepted forms:
        #   "Python Version Hint: 3.10"
        #   "Requires-Python: >=3.11"
        hint = self._extract_python_hint_from_summary(summary_content)
        if hint:
            return hint

        # 2) Scan repo for syntax triggers (only if repo_root given)
        if repo_root:
            try:
                min_ver = self._scan_repo_for_min_python(repo_root)
                if min_ver:
                    return min_ver
            except Exception as e:
                logger.warning(f"Python version inference scan failed: {e}")

        # 3) Fallback baseline (avoid 3.9; prefer modern default)
        return "3.11"

    def _extract_python_hint_from_summary(self, summary_content: str) -> Optional[str]:
        # simple patterns; extend if you write hints into summary later
        m = re.search(r"Python\s+Version\s+Hint:\s*([0-9]+\.[0-9]+)", summary_content, re.IGNORECASE)
        if m:
            return m.group(1)

        m = re.search(r"Requires-Python:\s*>=\s*([0-9]+\.[0-9]+)", summary_content, re.IGNORECASE)
        if m:
            return m.group(1)

        return None

    def _scan_repo_for_min_python(self, repo_root: str) -> Optional[str]:
        """
        Minimal scan:
        - Search .py files for match/case syntax triggers -> 3.10
        Keep it fast: scan a bounded number of files or size if needed.
        """
        root = Path(repo_root)
        if not root.exists():
            return None

        # Prefer scanning conftest.py and tests first (where you saw the failure)
        candidates = []
        for p in [root / "conftest.py", root / "tests"]:
            if p.exists():
                if p.is_file():
                    candidates.append(p)
                else:
                    candidates.extend(list(p.rglob("*.py")))

        # If nothing found, scan a limited subset of repo python files
        if not candidates:
            candidates = list(root.rglob("*.py"))[:500]  # cap to avoid huge repos

        for pyfile in candidates:
            try:
                text = self._read_text(str(pyfile))
                if any(rx.search(text) for rx in self._PY310_PATTERNS):
                    return "3.10"
            except Exception:
                continue

        return None

    def _choose_python_version(self, user_version: Optional[str], inferred_version: str) -> str:
        """
        Choose max(user_version, inferred_version) by major.minor comparison.
        If user_version is None -> inferred_version.
        """
        if not user_version:
            return inferred_version

        try:
            u = self._parse_major_minor(user_version)
            i = self._parse_major_minor(inferred_version)
            return user_version if u >= i else inferred_version
        except Exception:
            # If parsing fails, trust user input
            return user_version

    def _parse_major_minor(self, v: str) -> Tuple[int, int]:
        parts = v.strip().split(".")
        return int(parts[0]), int(parts[1])

    # ----------------------------
    # LLM + YAML post-processing
    # ----------------------------
    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a Conda expert. Output ONLY valid YAML."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    def _ensure_python_dep(self, env_yaml: str, python_version: str) -> str:
        """
        Ensure 'python=<version>' exists under dependencies.
        If python already present, do not try to rewrite aggressively (avoid corrupt YAML).
        """
        if re.search(r"^\s*-\s*python\s*=", env_yaml, re.MULTILINE):
            return env_yaml

        # Insert under dependencies: after the line 'dependencies:'
        lines = env_yaml.splitlines()
        out = []
        inserted = False
        for idx, line in enumerate(lines):
            out.append(line)
            if not inserted and re.match(r"^\s*dependencies:\s*$", line):
                # next indentation level is typically two spaces
                out.append(f"  - python={python_version}")
                inserted = True

        if not inserted:
            # fallback: append a minimal section (last resort)
            out.append("dependencies:")
            out.append(f"  - python={python_version}")

        return "\n".join(out).strip() + "\n"

    def _clean_markdown(self, content: str) -> str:
        if content.startswith("```"):
            lines = content.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()

    def _read_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def save_to_file(self, content: str, output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Environment.yml saved to: {output_path}")
