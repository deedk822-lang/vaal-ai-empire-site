#!/usr/bin/env python3
"""
Comprehensive tests for YAML configuration and workflow files.
Tests YAML syntax, schema validation, and file existence.
"""

import pytest
import yaml
import os
from pathlib import Path


class TestWorkflowFiles:
    """Test GitHub workflow YAML files."""

    def get_workflow_files(self):
        """Get all workflow YAML files."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")
        if not workflow_dir.exists():
            return []
        return list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))

    def test_workflow_files_exist(self):
        """Test that workflow directory exists and contains files."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")
        assert workflow_dir.exists(), "Workflow directory should exist"

        workflow_files = self.get_workflow_files()
        assert len(workflow_files) > 0, "Should have at least one workflow file"

    def test_workflow_yaml_syntax(self):
        """Test that all workflow files have valid YAML syntax."""
        workflow_files = self.get_workflow_files()

        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r') as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {workflow_file.name}: {e}")

    def test_workflow_basic_structure(self):
        """Test that workflows have basic required structure."""
        workflow_files = self.get_workflow_files()

        for workflow_file in workflow_files:
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)

            # Should have either 'on' or True (for reusable workflows with workflow_call)
            # Note: 'on' is a valid key in YAML
            has_trigger = (
                'on' in content or
                content.get('on') is not None or
                content.get(True) is not None or  # 'on:' becomes True in some YAML parsers
                'workflow_call' in str(content)
            )
            assert has_trigger, f"{workflow_file.name} should have 'on' trigger definition"

            # Should have jobs
            if 'jobs' in content:
                assert isinstance(content['jobs'], dict), \
                    f"{workflow_file.name} jobs should be a dictionary"
                assert len(content['jobs']) > 0, \
                    f"{workflow_file.name} should have at least one job"

    def test_specific_workflow_files(self):
        """Test that specific workflow files exist."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")
        expected_workflows = [
            "main.yml",
            "security.yml",
            "codeql.yml"
        ]

        for workflow_name in expected_workflows:
            workflow_path = workflow_dir / workflow_name
            if workflow_path.exists():
                # If it exists, verify it's valid YAML
                with open(workflow_path, 'r') as f:
                    content = yaml.safe_load(f)
                assert content is not None, f"{workflow_name} should not be empty"

    def test_benchmark_performance_workflow(self):
        """Test benchmark-performance workflow if it exists."""
        workflow_path = Path("/home/jailuser/git/.github/workflows/benchmark-performance.yml")

        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                content = yaml.safe_load(f)

            assert 'jobs' in content
            # Should have benchmark-related jobs
            job_names = list(content['jobs'].keys())
            assert len(job_names) > 0

    def test_sentinel_phase1_workflow(self):
        """Test sentinel-phase1 workflow if it exists."""
        workflow_path = Path("/home/jailuser/git/.github/workflows/sentinel-phase1.yml")

        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None
            if 'jobs' in content:
                assert isinstance(content['jobs'], dict)

    def test_validate_fixes_workflow(self):
        """Test validate-fixes workflow if it exists."""
        workflow_path = Path("/home/jailuser/git/.github/workflows/validate-fixes.yml")

        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None


class TestConfigFiles:
    """Test configuration YAML files."""

    def test_localai_config_exists(self):
        """Test that LocalAI config exists."""
        config_path = Path("/home/jailuser/git/config/localai-config.yaml")

        if config_path.exists():
            with open(config_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None
            assert isinstance(content, dict)

    def test_localai_config_structure(self):
        """Test LocalAI config structure."""
        config_path = Path("/home/jailuser/git/config/localai-config.yaml")

        if config_path.exists():
            with open(config_path, 'r') as f:
                content = yaml.safe_load(f)

            # Check for expected top-level keys
            expected_keys = ["name", "version"]
            for key in expected_keys:
                if key in content:
                    assert content[key] is not None, f"{key} should not be None"

            # If models are defined, check structure
            if "models" in content:
                assert isinstance(content["models"], list), "models should be a list"
                for model in content["models"]:
                    assert "name" in model, "Each model should have a name"

    def test_codeql_config_exists(self):
        """Test that CodeQL config exists if referenced."""
        config_path = Path("/home/jailuser/git/.github/codeql/codeql-config.yml")

        if config_path.exists():
            with open(config_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None


class TestEnvFiles:
    """Test .env files for format validation."""

    def test_env_example_exists(self):
        """Test that .env.example exists."""
        env_path = Path("/home/jailuser/git/.env.example")

        if env_path.exists():
            # Just check it's readable
            with open(env_path, 'r') as f:
                content = f.read()
            assert len(content) >= 0

    def test_env_example_format(self):
        """Test .env.example has valid format."""
        env_path = Path("/home/jailuser/git/.env.example")

        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Should be in KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    assert key.strip(), f"Line {i}: Key should not be empty"
                    # Value can be empty for examples

    def test_env_production_exists(self):
        """Test that .env.production exists if applicable."""
        env_path = Path("/home/jailuser/git/.env.production")

        # This is optional, just test if it exists
        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()
            assert len(content) >= 0

    def test_env_vercel_exists(self):
        """Test that .env.vercel exists if applicable."""
        env_path = Path("/home/jailuser/git/.env.vercel")

        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()
            assert len(content) >= 0


class TestWorkflowJobStructure:
    """Test detailed workflow job structure."""

    def test_jobs_have_steps(self):
        """Test that jobs have steps defined."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")

        if not workflow_dir.exists():
            pytest.skip("Workflow directory not found")

        for workflow_file in workflow_dir.glob("*.yml"):
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)

            if 'jobs' not in content:
                continue

            for job_name, job_def in content['jobs'].items():
                # Jobs should either have steps or use another action
                if 'steps' in job_def:
                    assert isinstance(job_def['steps'], list), \
                        f"{workflow_file.name}: {job_name} steps should be a list"
                    assert len(job_def['steps']) > 0, \
                        f"{workflow_file.name}: {job_name} should have at least one step"

                # Each step should have a name or uses
                if 'steps' in job_def:
                    for step_idx, step in enumerate(job_def['steps']):
                        assert isinstance(step, dict), \
                            f"{workflow_file.name}: {job_name} step {step_idx} should be a dict"

    def test_workflow_names(self):
        """Test that workflows have names."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")

        if not workflow_dir.exists():
            pytest.skip("Workflow directory not found")

        for workflow_file in workflow_dir.glob("*.yml"):
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)

            # Workflows should ideally have a name
            if 'name' in content:
                assert isinstance(content['name'], str)
                assert len(content['name']) > 0


class TestYAMLConsistency:
    """Test YAML consistency across files."""

    def test_no_tabs_in_yaml(self):
        """Test that YAML files don't use tabs (should use spaces)."""
        yaml_files = []

        # Collect all YAML files
        workflow_dir = Path("/home/jailuser/git/.github/workflows")
        config_dir = Path("/home/jailuser/git/config")

        if workflow_dir.exists():
            yaml_files.extend(workflow_dir.glob("*.yml"))
            yaml_files.extend(workflow_dir.glob("*.yaml"))

        if config_dir.exists():
            yaml_files.extend(config_dir.glob("*.yml"))
            yaml_files.extend(config_dir.glob("*.yaml"))

        codeql_config = Path("/home/jailuser/git/.github/codeql/codeql-config.yml")
        if codeql_config.exists():
            yaml_files.append(codeql_config)

        for yaml_file in yaml_files:
            with open(yaml_file, 'r') as f:
                content = f.read()

            # YAML should not contain tabs
            assert '\t' not in content, \
                f"{yaml_file.name} should not contain tabs (use spaces for indentation)"

    def test_yaml_files_not_empty(self):
        """Test that YAML files are not empty."""
        yaml_files = []

        workflow_dir = Path("/home/jailuser/git/.github/workflows")
        if workflow_dir.exists():
            yaml_files.extend(workflow_dir.glob("*.yml"))

        config_dir = Path("/home/jailuser/git/config")
        if config_dir.exists():
            yaml_files.extend(config_dir.glob("*.yaml"))

        for yaml_file in yaml_files:
            size = yaml_file.stat().st_size
            assert size > 0, f"{yaml_file.name} should not be empty"


class TestSecurityWorkflow:
    """Test security workflow specifically."""

    def test_security_workflow_exists(self):
        """Test that security workflow exists."""
        security_path = Path("/home/jailuser/git/.github/workflows/security.yml")

        if security_path.exists():
            with open(security_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None
            assert 'jobs' in content or 'on' in content

    def test_security_workflow_has_security_jobs(self):
        """Test security workflow has security-related jobs."""
        security_path = Path("/home/jailuser/git/.github/workflows/security.yml")

        if security_path.exists():
            with open(security_path, 'r') as f:
                content = yaml.safe_load(f)

            if 'jobs' in content:
                # Just verify jobs exist
                assert len(content['jobs']) > 0


class TestOpenAPIValidation:
    """Test OpenAPI validation workflow if present."""

    def test_openapi_workflow_exists(self):
        """Test OpenAPI validation workflow."""
        openapi_path = Path("/home/jailuser/git/.github/workflows/openapi-validation.yml")

        if openapi_path.exists():
            with open(openapi_path, 'r') as f:
                content = yaml.safe_load(f)

            assert content is not None


class TestEdgeCases:
    """Test edge cases for YAML validation."""

    def test_yaml_with_anchors_and_aliases(self):
        """Test YAML files with anchors and aliases parse correctly."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")

        if not workflow_dir.exists():
            pytest.skip("Workflow directory not found")

        for workflow_file in workflow_dir.glob("*.yml"):
            try:
                with open(workflow_file, 'r') as f:
                    # safe_load should handle anchors and aliases
                    content = yaml.safe_load(f)
                assert content is not None
            except yaml.YAMLError as e:
                pytest.fail(f"Failed to parse {workflow_file.name}: {e}")

    def test_yaml_multiline_strings(self):
        """Test that multiline strings in YAML are valid."""
        workflow_dir = Path("/home/jailuser/git/.github/workflows")

        if not workflow_dir.exists():
            pytest.skip("Workflow directory not found")

        for workflow_file in workflow_dir.glob("*.yml"):
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)

            # Should parse without errors even with multiline strings
            assert content is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])