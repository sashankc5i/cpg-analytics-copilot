class ToolError(Exception):
    """User/LLM-correctable validation error."""


class PolicyError(Exception):
    """Blocked by RBAC / row-level security."""
