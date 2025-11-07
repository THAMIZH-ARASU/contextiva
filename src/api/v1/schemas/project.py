"""Pydantic schemas for Project API endpoints."""

from __future__ import annotations

import re
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    tags: Optional[List[str]] = Field(None, description="List of project tags")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Project name must not be empty or whitespace only")
        return v.strip()
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tag format: alphanumeric, underscore, hyphen only."""
        if v is None:
            return None
        
        for tag in v:
            if not isinstance(tag, str) or not tag:
                raise ValueError("Each tag must be a non-empty string")
            if not re.match(r"^[A-Za-z0-9_-]+$", tag):
                raise ValueError("Tags may only contain letters, numbers, underscore, and hyphen")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "My AI Agent Project",
                    "description": "A project for managing AI agent knowledge",
                    "tags": ["ai", "nlp", "agent-1"]
                }
            ]
        }
    }


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    status: Optional[str] = Field(None, description="Project status: Active or Archived")
    tags: Optional[List[str]] = Field(None, description="List of project tags")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate that name is not just whitespace if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Project name must not be empty or whitespace only")
        return v.strip() if v else None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status is either Active or Archived."""
        if v is not None and v not in {"Active", "Archived"}:
            raise ValueError("Status must be either 'Active' or 'Archived'")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tag format: alphanumeric, underscore, hyphen only."""
        if v is None:
            return None
        
        for tag in v:
            if not isinstance(tag, str) or not tag:
                raise ValueError("Each tag must be a non-empty string")
            if not re.match(r"^[A-Za-z0-9_-]+$", tag):
                raise ValueError("Tags may only contain letters, numbers, underscore, and hyphen")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Project Name",
                    "status": "Archived",
                    "tags": ["updated", "v2"]
                }
            ]
        }
    }


class ProjectResponse(BaseModel):
    """Schema for project responses."""
    
    id: UUID = Field(..., description="Project unique identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    tags: Optional[List[str]] = Field(None, description="List of project tags")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "My AI Agent Project",
                    "description": "A project for managing AI agent knowledge",
                    "status": "Active",
                    "tags": ["ai", "nlp", "agent-1"]
                }
            ]
        }
    }
