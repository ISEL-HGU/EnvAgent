"""
Decision Agent (Refactored Final Version).
Analyzes project structure, detects Monorepo roots, and decides analysis strategy.
"""

import logging
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

class DecisionAgent:
    """Analyzes project structure to determine the best environment creation strategy."""

    # Priority order for configuration files
    ENV_FILES_PRIORITY = [
        'environment.yml', 'environment.yaml', 'conda.yaml',  # 1. Conda native
        'requirements.txt', 'requirements-dev.txt',           # 2. Pip standard
        'setup.py', 'pyproject.toml', 'Pipfile',              # 3. Python packaging
        'Dockerfile', 'docker-compose.yml'                    # 4. Container (Last resort)
    ]

    DECISION_PROMPT = """You are a Python DevOps expert. Analyze the project to choose the best environment strategy.

Context:
- Path: {current_path}
- Files: {existing_files}
- README Snippet: {readme_content}

Goal:
Determine if we can use existing files or need deep code analysis.

Rules:
1. If 'environment.yml' or robust 'requirements.txt' exists -> has_env_setup=true, proceed=false.
2. If ONLY Docker files exist -> has_env_setup=true (type: docker), proceed=true (need to parse dockerfile).
3. If no config files -> proceed=true.

Output JSON:
{{
    "has_env_setup": boolean,
    "env_type": "conda" | "pip" | "docker" | "poetry" | "none",
    "env_file": "path/to/best_file" or null,
    "proceed_with_analysis": boolean,
    "reason": "short explanation"
}}
"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.api_key)
        logger.info("DecisionAgent initialized")

    # ----------------------------------------------------------------
    # 1. Main Decision Logic
    # ----------------------------------------------------------------
    def decide(self, input_path: str) -> Dict[str, Any]:
        """Main entry point for decision making."""
        logger.info(f"Analyzing project starting from: {input_path}")
        input_dir = Path(input_path).resolve()

        # 1. Monorepo Detection (Find True Root)
        target_directory = self._find_true_project_root(input_dir)
        if target_directory != input_dir:
            logger.info(f"🚀 Monorepo detected! Redirecting to: {target_directory}")

        # 2. Scan for config files in the true root
        existing_files = self._scan_env_files(target_directory)

        # 3. Try Fast Track (Rule-based Decision)
        fast_decision = self._try_fast_track_decision(existing_files, target_directory)
        if fast_decision:
            logger.info(f"Fast track decision: {fast_decision['reason']}")
            return fast_decision

        # 4. Fallback to LLM Decision
        logger.info("No obvious config found. Consulting LLM...")
        return self._ask_llm_for_decision(target_directory, existing_files)

    # ----------------------------------------------------------------
    # 2. Internal Core Logic
    # ----------------------------------------------------------------
    def _find_true_project_root(self, start_path: Path) -> Path:
        """
        Scoring algorithm to find the 'real' project root.
        Improved: Scans deeper (depth=4) but skips junk folders for speed.
        """
        MAX_SCAN_DEPTH = 4 
        
        candidates = []
        
        IGNORED_DIRS = {
            '.git', '.idea', '.vscode', '__pycache__', 
            'node_modules', 'venv', 'env', '.env', 'dist', 'build'
        }

        for root, dirs, files in os.walk(start_path):
            current = Path(root)
            
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            try:
                depth = len(current.relative_to(start_path).parts)
            except ValueError:
                continue

            if depth > MAX_SCAN_DEPTH:
                del dirs[:] 
                continue
                
            score = 0
            if any(f in files for f in ['setup.py', 'pyproject.toml', 'environment.yml', 'conda.yaml']):
                score += 10
            
            if 'requirements.txt' in files:
                score += 5
            if 'src' in dirs or 'app' in dirs:
                score += 5

            if current.name.lower() in ['docs', 'tests', 'examples', 'scripts']:
                score -= 10
            
            if score > 0:
                candidates.append((score, current))
        
        if not candidates:
            return start_path
            
        candidates.sort(key=lambda x: (-x[0], len(str(x[1]))))
        
        best_path = candidates[0][1]
        
        if best_path != start_path:
            logger.debug(f"Root switched: {start_path} -> {best_path} (Score: {candidates[0][0]})")
            
        return best_path

    def _scan_env_files(self, path: Path) -> List[Dict]:
        found = []
        for name in self.ENV_FILES_PRIORITY:
            f = path / name
            if f.exists():
                found.append({"name": name, "path": str(f), "size": f.stat().st_size})
        return found

    def _try_fast_track_decision(self, files: List[Dict], target_dir: Path) -> Optional[Dict]:
        """Returns a decision dict if a clear winner exists, else None."""
        for f in files:
            name = f['name']
            if f['size'] < 10: continue  # Skip empty files

            # Priority 1: Conda files (Gold Standard)
            if name in ['environment.yml', 'environment.yaml', 'conda.yaml']:
                return self._build_response(True, "conda", f['path'], target_dir, False, "Valid Conda environment file found.")
            
            # Priority 2: setup.py (Python Standard)
            if name == 'setup.py':
                return self._build_response(True, "pip", f['path'], target_dir, False, "Found setup.py (installable package).")
            
            # Priority 3: requirements.txt (Common Standard)
            if name == 'requirements.txt':
                return self._build_response(True, "pip", f['path'], target_dir, False, "Found requirements.txt.")
        
        return None

    def _ask_llm_for_decision(self, target_dir: Path, files: List[Dict]) -> Dict:
        readme = self._read_readme(target_dir)
        files_str = "\n".join([f"- {f['name']}" for f in files]) if files else "None"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "user", "content": self.DECISION_PROMPT.format(
                        current_path=target_dir.name,
                        existing_files=files_str,
                        readme_content=readme[:2000] if readme else "No README"
                    )}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            result['target_directory'] = str(target_dir)
            return result
        except Exception as e:
            logger.error(f"LLM Decision failed: {e}")
            # Safe Fallback: Just analyze everything
            return self._build_response(False, "none", None, target_dir, True, "LLM failed, falling back to deep analysis.")

    # ----------------------------------------------------------------
    # 3. Helper Methods (Extraction & Utils)
    # ----------------------------------------------------------------
    def collect_env_files_content(self, project_path: str) -> str:
        """
        Collect content from environment files for the Builder to use.
        Reads files in priority order and extracts relevant parts.
        """
        logger.info(f"Collecting content from: {project_path}")
        project_dir = Path(project_path).resolve()
        consolidated_parts = []

        for env_file in self.ENV_FILES_PRIORITY:
            file_path = project_dir / env_file
            
            if file_path.exists() and file_path.stat().st_size > 0:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                    if env_file == 'setup.py':
                        deps = self._extract_setup_py_deps(content)
                        if deps:
                            consolidated_parts.append(f"=== {env_file} (install_requires) ===\n{deps}\n")
                    
                    elif env_file == 'pyproject.toml':
                        deps = self._extract_pyproject_deps(content)
                        if deps:
                            consolidated_parts.append(f"=== {env_file} (dependencies) ===\n{deps}\n")
                    
                    else:
                        consolidated_parts.append(f"=== {env_file} ===\n{content}\n")
                        
                except Exception as e:
                    logger.warning(f"Error reading {env_file}: {e}")

        return "\n".join(consolidated_parts) if consolidated_parts else ""

    def _extract_setup_py_deps(self, content: str) -> str:
        """Extract install_requires from setup.py using regex."""
        match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            deps_text = match.group(1)
            deps = re.findall(r'["\']([^"\']+)["\']', deps_text)
            return '\n'.join(deps)
        return ""

    def _extract_pyproject_deps(self, content: str) -> str:
        """Extract dependencies from pyproject.toml using regex."""
        match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            deps_text = match.group(1)
            deps = re.findall(r'["\']([^"\']+)["\']', deps_text)
            return '\n'.join(deps)
        return ""

    def _read_readme(self, path: Path) -> Optional[str]:
        for n in ['README.md', 'README.txt', 'README']:
            p = path / n
            if p.exists():
                try: 
                    return p.read_text(encoding='utf-8', errors='ignore')
                except: pass
        return None

    def _build_response(self, has_setup, type_, file_, target, proceed, reason):
        return {
            "has_env_setup": has_setup,
            "env_type": type_,
            "env_file": file_,
            "target_directory": str(target),
            "proceed_with_analysis": proceed,
            "reason": reason
        }