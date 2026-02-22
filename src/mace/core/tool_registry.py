"""
MACE Core: Tool Registry

The "Hands" of the Organism.
Maps tool names to callable functions.
All tools must be governance-approved before registration.

Scientific Basis: This is the "Motor Cortex" - purely executive, no decision-making.
ZDP Compliance: Tools are externalities; they cannot alter the Symbolic Core.
"""

from typing import Dict, Callable, Any, Optional
import importlib
import os

class ToolRegistry:
    """
    Central registry for all executable tools.
    Tools are governance-gated: only approved modules are loadable.
    """
    
    # Whitelist of safe imports for dynamic tools
    SAFE_IMPORTS = frozenset([
        "os.path", "json", "re", "math", "datetime", "hashlib", 
        "base64", "urllib.parse", "collections", "itertools"
    ])
    
    # Forbidden imports (Security: ZDP Rule 03 - No Auth Bypass)
    FORBIDDEN_IMPORTS = frozenset([
        "subprocess", "os.system", "eval", "exec", "compile",
        "socket", "http.client", "requests", "urllib.request"
    ])
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._register_builtins()
        
    def _register_builtins(self):
        """Register core built-in tools."""
        self.register("echo", self._tool_echo, {"description": "Returns input as output"})
        self.register("log", self._tool_log, {"description": "Logs data to cognitive stream"})
        self.register("noop", self._tool_noop, {"description": "No operation"})
        
    def _tool_echo(self, **kwargs) -> Dict[str, Any]:
        """Built-in: Echo tool."""
        return {"result": kwargs.get("input", ""), "status": "success"}
        
    def _tool_log(self, **kwargs) -> Dict[str, Any]:
        """Built-in: Log tool."""
        message = kwargs.get("message", "")
        print(f"[MACE LOG] {message}")
        return {"logged": message, "status": "success"}
        
    def _tool_noop(self, **kwargs) -> Dict[str, Any]:
        """Built-in: No-op tool."""
        return {"status": "noop", "reason": kwargs.get("reason", "no action required")}
        
    def register(self, name: str, func: Callable, metadata: Optional[Dict] = None):
        """
        Register a tool.
        
        Args:
            name: Unique tool identifier
            func: Callable that takes **kwargs and returns Dict
            metadata: Optional metadata (description, author, version)
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered.")
        self._tools[name] = func
        self._metadata[name] = metadata or {}
        
    def get(self, name: str) -> Optional[Callable]:
        """Retrieve a tool by name."""
        return self._tools.get(name)
        
    def has(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools
        
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tools with metadata."""
        return {name: self._metadata.get(name, {}) for name in self._tools.keys()}
        
    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name.
        
        Returns:
            Result dict with at minimum {"status": "success|error"}
        """
        tool = self.get(name)
        if not tool:
            return {"status": "error", "error": f"Tool '{name}' not found"}
            
        try:
            result = tool(**kwargs)
            if not isinstance(result, dict):
                result = {"result": result, "status": "success"}
            return result
        except Exception as e:
            return {"status": "error", "error": str(e), "tool": name}
            
    def load_dynamic_tool(self, module_path: str, tool_name: str) -> bool:
        """
        Load a dynamically created tool from the dynamic tools directory.
        
        Security: Only loads from approved directory with governance check.
        """
        dynamic_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "dynamic")
        safe_path = os.path.abspath(os.path.join(dynamic_dir, f"{module_path}.py"))
        
        # Security: Ensure path is within dynamic directory
        if not safe_path.startswith(os.path.abspath(dynamic_dir)):
            raise SecurityError(f"Attempted path traversal: {module_path}")
            
        if not os.path.exists(safe_path):
            return False
            
        # Import the module
        spec = importlib.util.spec_from_file_location(module_path, safe_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the main function
        if hasattr(module, "main"):
            self.register(tool_name, module.main, {"dynamic": True, "path": safe_path})
            return True
        return False


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


# Global singleton
_REGISTRY: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ToolRegistry()
    return _REGISTRY
