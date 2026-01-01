"""
Memory dataclass for storing analysis results between agents.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Memory:
    """
    Shared memory for storing project analysis results.
    Used to pass information between agents.
    """

    project_name: str = ""
    package_list: List[str] = field(default_factory=list)
    python_version: str = ""
    cuda_version: Optional[str] = None
    cudnn_version: Optional[str] = None
    system_dependencies: List[str] = field(default_factory=list)
    raw_analysis: str = ""
    error_history: List[Tuple[str, str]] = field(default_factory=list)  # (error, fix_description)

    def __repr__(self) -> str:
        """Return a string representation of the Memory."""
        return (
            f"Memory(\n"
            f"  project_name='{self.project_name}',\n"
            f"  python_version='{self.python_version}',\n"
            f"  packages={len(self.package_list)},\n"
            f"  cuda_version='{self.cuda_version}',\n"
            f"  cudnn_version='{self.cudnn_version}',\n"
            f"  system_deps={len(self.system_dependencies)}\n"
            f")"
        )
