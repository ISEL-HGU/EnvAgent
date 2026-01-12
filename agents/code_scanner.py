"""
Code Scanner Agent (Refactored).
Performs Static Analysis (AST) to extract imports from Python source code.
Now supports .py and .ipynb files.
"""

import ast
import json
import logging
import sys
from pathlib import Path
from typing import List, Set, Tuple, Optional

logger = logging.getLogger(__name__)

class CodeScannerAgent:
    """
    Analyzes source code to extract import statements and detect CUDA usage.
    """

    # Expanded Standard Library List (Python 3.8+)
    # These should NOT appear in requirements.txt
    STD_LIB = set(sys.builtin_module_names) | {
        'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'copy', 'csv',
        'datetime', 'decimal', 'distutils', 'email', 'enum', 'functools', 'glob',
        'gzip', 'hashlib', 'html', 'http', 'importlib', 'inspect', 'io', 'json',
        'logging', 'math', 'multiprocessing', 'os', 'pathlib', 'pickle', 'platform',
        'pprint', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl',
        'stat', 'string', 'subprocess', 'sys', 'tempfile', 'threading', 'time',
        'timeit', 'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref',
        'xml', 'zipfile', 'zoneinfo'
    }

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def scan_files(self, file_paths: List[Path], root_dir: Path, project_name: str) -> Path:
        """
        Main entry point: Scans a list of files for dependencies.
        """
        all_imports = set()
        cuda_required = False
        dependency_hints = []

        logger.info(f"🔬 Static Analysis: Scanning {len(file_paths)} files in {root_dir.name}...")

        for file_path in file_paths:
            try:
                # 1. Analyze Source Code (.py & .ipynb)
                if file_path.suffix in ['.py', '.ipynb']:
                    imports, has_cuda = self._scan_source_file(file_path)
                    all_imports.update(imports)
                    if has_cuda:
                        cuda_required = True
                
                # 2. Collect Config Hints (requirements.txt, etc.)
                # These are just read as text to provide context for GPT-4 later
                if file_path.name in ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile']:
                    content = self._read_file_safe(file_path)
                    if content:
                        hint_block = f"--- Content of {file_path.name} ---\n{content[:3000]}\n"
                        dependency_hints.append(hint_block)

            except Exception as e:
                logger.warning(f"Failed to scan {file_path.name}: {e}")

        # 3. Generate Summary Report
        summary_filename = f"dependency_summary_{project_name}.txt"
        output_path = self.output_dir / summary_filename

        self._write_summary(output_path, all_imports, cuda_required, project_name, dependency_hints)
        
        return output_path

    def _scan_source_file(self, file_path: Path) -> Tuple[Set[str], bool]:
        """Dispatches to correct scanner based on file extension."""
        if file_path.suffix == '.ipynb':
            return self._scan_notebook(file_path)
        return self._scan_python(file_path)

    def _scan_python(self, file_path: Path) -> Tuple[Set[str], bool]:
        """Extract imports from .py file using AST."""
        imports = set()
        has_cuda = False
        
        content = self._read_file_safe(file_path)
        if not content:
            return imports, has_cuda

        # Simple string check for CUDA usage
        if self._check_cuda_usage(content):
            has_cuda = True

        # AST Parsing
        try:
            tree = ast.parse(content)
            imports.update(self._extract_imports_from_ast(tree))
        except SyntaxError:
            logger.debug(f"Syntax error in {file_path.name} (skipping AST)")
        except Exception:
            pass
            
        return imports, has_cuda

    def _scan_notebook(self, file_path: Path) -> Tuple[Set[str], bool]:
        """Extract imports from .ipynb file (Jupyter Notebook)."""
        imports = set()
        has_cuda = False
        
        content = self._read_file_safe(file_path)
        if not content:
            return imports, has_cuda

        try:
            notebook = json.loads(content)
            # Combine all code cells into one string
            code_content = ""
            for cell in notebook.get('cells', []):
                if cell.get('cell_type') == 'code':
                    code_content += "".join(cell.get('source', [])) + "\n"
            
            if self._check_cuda_usage(code_content):
                has_cuda = True
                
            # Parse the combined code
            tree = ast.parse(code_content)
            imports.update(self._extract_imports_from_ast(tree))
            
        except Exception:
            # Notebooks often have magic commands (%) that break AST
            # In a real product, we would clean them, but here we just skip if it fails
            pass
            
        return imports, has_cuda

    def _extract_imports_from_ast(self, tree: ast.AST) -> Set[str]:
        """Helper to walk AST and find import nodes."""
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    found.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # e.g., 'from sklearn.metrics import ...' -> 'sklearn'
                    found.add(node.module.split('.')[0])
        return found

    def _check_cuda_usage(self, content: str) -> bool:
        """Heuristic check for GPU/CUDA usage."""
        lower = content.lower()
        keywords = ['cuda', 'gpu', 'torch.device', 'tensorflow-gpu']
        return any(k in lower for k in keywords)

    def _read_file_safe(self, path: Path) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return ""

    def _write_summary(self, path: Path, imports: Set[str], cuda_required: bool, project_name: str, hints: List[str]):
        """Saves the analysis result to a text file for the next agent."""
        # Filter out standard library modules
        filtered_imports = sorted([
            imp for imp in imports 
            if imp not in self.STD_LIB and not imp.startswith('_')
        ])

        lines = [
            f"# Dependency Summary for {project_name}",
            f"# Generated by EnvAgent CodeScanner",
            "",
            f"CUDA Required: {'Yes' if cuda_required else 'No'}",
            "",
            "## Detected Third-Party Imports (AST Analysis):",
        ]
        
        if filtered_imports:
            lines.extend([f"- {imp}" for imp in filtered_imports])
        else:
            lines.append("(No third-party imports detected)")
            
        lines.append("")
        lines.append("## Configuration File Hints:")
        if hints:
            lines.extend(hints)
        else:
            lines.append("(No configuration files found)")

        path.write_text('\n'.join(lines), encoding='utf-8')
        logger.info(f"Summary saved to {path}")