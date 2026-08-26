import yaml
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class ConfigValidationError(Exception):
    pass

def _default_custom_excludes() -> List[str]:
    # Legacy v0.1.0 ignored directories (excluding .git and .docswarm which are mandatory)
    return [
        ".venv", "node_modules", "__pycache__", "dist", "build", 
        ".pytest_cache", ".idea", ".vscode", "vendor", "target", "out", 
        "coverage", "env", "venv"
    ]

class ScannerConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_file_size_kb: int = 2048
    custom_excludes: List[str] = Field(default_factory=_default_custom_excludes)

class RoleConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role_name: str
    patterns: List[str]

class RuleConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    source_role: str
    forbidden_target_role: str
    severity: str
    penalty: int
    message: str

def _default_roles() -> List[RoleConfig]:
    return [
        RoleConfig(role_name="Controller", patterns=["*controller*"]),
        RoleConfig(role_name="Service", patterns=["*service*"]),
        RoleConfig(role_name="Model", patterns=["*model*", "*entity*", "models/*"]),
        RoleConfig(role_name="Repository", patterns=["*repository*", "*dao*", "*repo*"]),
        RoleConfig(role_name="Utility", patterns=["*util*", "*helper*"]),
        RoleConfig(role_name="Component", patterns=["*component*", "*.tsx", "*.jsx"]),
        RoleConfig(role_name="Entry Point", patterns=["*main*", "*index*", "*app*"]),
    ]

def _default_rules() -> List[RuleConfig]:
    return [
        RuleConfig(
            id="ARCH-002",
            source_role="Model",
            forbidden_target_role="Controller",
            severity="medium",
            penalty=10,
            message="Model depends on Controller."
        ),
        RuleConfig(
            id="ARCH-003",
            source_role="Model",
            forbidden_target_role="Service",
            severity="low",
            penalty=5,
            message="Model depends on Service."
        )
    ]

class DocSwarmConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal["1.0"] = "1.0"
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    roles: List[RoleConfig] = Field(default_factory=_default_roles)
    rules: List[RuleConfig] = Field(default_factory=_default_rules)


def load_config(target_workspace: str | Path) -> DocSwarmConfig:
    """
    Loads .docswarm.yaml strictly from the target workspace.
    Returns default config if missing.
    Raises ConfigValidationError if malformed.
    """
    target = Path(target_workspace).resolve()
    config_file = target / ".docswarm.yaml"
    
    if not config_file.exists():
        return DocSwarmConfig()
        
    try:
        content = config_file.read_text(encoding="utf-8")
        raw_config = yaml.safe_load(content)
        
        # If the file is empty, yaml.safe_load returns None
        if raw_config is None:
            raw_config = {}
            
        if not isinstance(raw_config, dict):
            raise ConfigValidationError("Configuration file must contain a YAML dictionary.")
            
        return DocSwarmConfig.model_validate(raw_config)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML syntax in .docswarm.yaml: {e}")
    except ValidationError as e:
        raise ConfigValidationError(f"Schema validation error in .docswarm.yaml:\n{e}")
