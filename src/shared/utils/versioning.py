"""Utility functions for semantic versioning."""

import re
from typing import Literal


def bump_version(current_version: str, bump_type: Literal["major", "minor", "patch"]) -> str:
    """
    Bump a semantic version string.
    
    Args:
        current_version: Current version (e.g., "v1.2.3" or "1.2.3")
        bump_type: Type of version bump ("major", "minor", or "patch")
        
    Returns:
        New bumped version string with 'v' prefix (e.g., "v2.0.0")
        
    Raises:
        ValueError: If version format is invalid
        
    Examples:
        >>> bump_version("v1.2.3", "major")
        'v2.0.0'
        >>> bump_version("v1.2.3", "minor")
        'v1.3.0'
        >>> bump_version("v1.2.3", "patch")
        'v1.2.4'
        >>> bump_version("1.2.3", "major")
        'v2.0.0'
    """
    # Remove 'v' prefix if present
    version = current_version.lstrip("v")
    
    # Validate semantic version format
    pattern = r"^(\d+)\.(\d+)\.(\d+)$"
    match = re.match(pattern, version)
    
    if not match:
        raise ValueError(
            f"Invalid semantic version format: {current_version}. "
            "Expected format: v1.2.3 or 1.2.3"
        )
    
    major, minor, patch = map(int, match.groups())
    
    # Bump version based on type
    if bump_type == "major":
        return f"v{major + 1}.0.0"
    elif bump_type == "minor":
        return f"v{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump_type: {bump_type}. Must be 'major', 'minor', or 'patch'")
