import pytest
from pathlib import Path
from core.config import (
    load_config, DocSwarmConfig, ConfigValidationError
)

def test_default_config_preserves_v010():
    config = DocSwarmConfig()
    
    assert config.schema_version == "1.0"
    assert config.scanner.max_file_size_kb == 2048
    assert len(config.scanner.custom_excludes) == 14
    assert "node_modules" in config.scanner.custom_excludes
    
    assert len(config.roles) == 7
    assert config.roles[0].role_name == "Controller"
    
    assert len(config.rules) == 2
    assert config.rules[0].id == "ARCH-002"

def test_default_object_isolation():
    config1 = DocSwarmConfig()
    config2 = DocSwarmConfig()
    
    # Mutating one config doesn't mutate another
    config1.scanner.max_file_size_kb = 1000
    config1.roles.pop() # Modify the list
    
    assert config2.scanner.max_file_size_kb == 2048
    assert len(config2.roles) == 7

def test_missing_yaml_uses_defaults(tmp_path):
    config = load_config(tmp_path)
    assert config.scanner.max_file_size_kb == 2048

def test_parent_directory_configuration_isolation(tmp_path):
    # Put .docswarm.yaml in parent directory
    parent_yaml = tmp_path / ".docswarm.yaml"
    parent_yaml.write_text("schema_version: '1.0'\nscanner:\n  max_file_size_kb: 9999", encoding="utf-8")
    
    child_dir = tmp_path / "child"
    child_dir.mkdir()
    
    # load_config from child should ignore parent and return defaults
    config = load_config(child_dir)
    assert config.scanner.max_file_size_kb == 2048

def test_load_valid_yaml_partial_scanner_max_size(tmp_path):
    # Case A: scanner max size
    yaml_content = "scanner:\n  max_file_size_kb: 4096\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    config = load_config(tmp_path)
    
    assert config.scanner.max_file_size_kb == 4096
    assert len(config.scanner.custom_excludes) == 14

def test_load_valid_yaml_partial_scanner_excludes(tmp_path):
    # Case B: scanner custom excludes
    yaml_content = "scanner:\n  custom_excludes:\n    - generated\n    - tmp\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    config = load_config(tmp_path)
    
    assert config.scanner.max_file_size_kb == 2048
    assert config.scanner.custom_excludes == ["generated", "tmp"]

def test_load_valid_yaml_partial_roles_replacement(tmp_path):
    # Case C: roles replacement
    yaml_content = "roles:\n  - role_name: Service\n    patterns:\n      - '*svc*'\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    config = load_config(tmp_path)
    
    # List should be strictly replaced, not merged
    assert len(config.roles) == 1
    assert config.roles[0].role_name == "Service"
    assert config.roles[0].patterns == ["*svc*"]

def test_load_valid_yaml_partial_rules_replacement(tmp_path):
    # Case D: rules replacement
    yaml_content = "rules:\n  - id: CUSTOM-001\n    source_role: Model\n    forbidden_target_role: Controller\n    severity: medium\n    penalty: 5\n    message: '...'\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    config = load_config(tmp_path)
    
    # List should be strictly replaced
    assert len(config.rules) == 1
    assert config.rules[0].id == "CUSTOM-001"
    assert config.rules[0].penalty == 5

def test_schema_version_semantics(tmp_path):
    # Missing schema_version -> defaults to 1.0
    yaml_content = "scanner:\n  max_file_size_kb: 4096\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    assert load_config(tmp_path).schema_version == "1.0"
    
    # Explicit 1.0 -> accepted
    yaml_content2 = "schema_version: '1.0'\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content2, encoding="utf-8")
    assert load_config(tmp_path).schema_version == "1.0"
    
    # Unsupported schema_version -> validation error
    yaml_content3 = "schema_version: '2.0'\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content3, encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc:
        load_config(tmp_path)
    assert "Input should be '1.0'" in str(exc.value)

def test_loading_yaml_does_not_mutate_defaults(tmp_path):
    # Ensure parsing a config doesn't mess up future default generations
    yaml_content = "scanner:\n  max_file_size_kb: 9999\n"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    config1 = load_config(tmp_path)
    assert config1.scanner.max_file_size_kb == 9999
    
    config2 = DocSwarmConfig()
    assert config2.scanner.max_file_size_kb == 2048

def test_malformed_yaml_syntax(tmp_path):
    yaml_content = "scanner:\n  - max_file_size_kb: 4096\n  custom_excludes: ["
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    
    with pytest.raises(ConfigValidationError) as exc:
        load_config(tmp_path)
    assert "Invalid YAML syntax" in str(exc.value)

def test_unknown_top_level_field(tmp_path):
    yaml_content = "schema_version: '1.0'\nunknown_field: true"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    
    with pytest.raises(ConfigValidationError) as exc:
        load_config(tmp_path)
    assert "Schema validation error" in str(exc.value)
    assert "Extra inputs are not permitted" in str(exc.value)

def test_unknown_nested_field(tmp_path):
    yaml_content = "schema_version: '1.0'\nscanner:\n  fake_prop: 123"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    
    with pytest.raises(ConfigValidationError) as exc:
        load_config(tmp_path)
    assert "Schema validation error" in str(exc.value)
    assert "Extra inputs are not permitted" in str(exc.value)
def test_invalid_type(tmp_path):
    yaml_content = "schema_version: '1.0'\nscanner:\n  max_file_size_kb: 'huge'"
    (tmp_path / ".docswarm.yaml").write_text(yaml_content, encoding="utf-8")
    
    with pytest.raises(ConfigValidationError) as exc:
        load_config(tmp_path)
    assert "Schema validation error" in str(exc.value)

def test_analysis_service_injection():
    from core.engine import AnalysisService
    
    # Defaults
    engine = AnalysisService()
    assert engine.config.scanner.max_file_size_kb == 2048
    
    # Custom
    custom_config = DocSwarmConfig()
    custom_config.scanner.max_file_size_kb = 1234
    
    engine2 = AnalysisService(config=custom_config)
    assert engine2.config.scanner.max_file_size_kb == 1234

def test_role_precedence():
    # Verify that the defaults list preserves the v0.1.0 precedence.
    # Order determines precedence.
    config = DocSwarmConfig()
    role_names = [r.role_name for r in config.roles]
    
    # Expected precedence based on v0.1.0 heuristics:
    expected = [
        "Controller",
        "Service",
        "Model",
        "Repository",
        "Utility",
        "Component",
        "Entry Point"
    ]
    assert role_names == expected
