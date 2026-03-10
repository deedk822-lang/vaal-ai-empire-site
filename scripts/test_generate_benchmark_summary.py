#!/usr/bin/env python3
"""
Comprehensive tests for Benchmark Summary Generator.
Tests JSON loading, table rendering, summary generation, and CLI.
"""

import pytest
import json
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
from generate_benchmark_summary import (
    load_json_file,
    render_backend_table,
    generate_summary,
    main
)


class TestLoadJsonFile:
    """Test JSON file loading."""

    def test_load_valid_json(self):
        """Test loading a valid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"key": "value"}, f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result is not None
            assert result["key"] == "value"
        finally:
            temp_path.unlink()

    def test_load_non_existent_file(self):
        """Test loading a non-existent file."""
        result = load_json_file(Path("/non/existent/file.json"))
        assert result is None

    def test_load_invalid_json(self):
        """Test loading invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result is None
        finally:
            temp_path.unlink()

    def test_load_non_dict_json(self):
        """Test loading JSON that's not a dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(["not", "a", "dict"], f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result is None
        finally:
            temp_path.unlink()

    def test_load_empty_dict(self):
        """Test loading an empty dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result is not None
            assert result == {}
        finally:
            temp_path.unlink()


class TestRenderBackendTable:
    """Test backend table rendering."""

    def test_render_with_valid_data(self):
        """Test rendering table with valid data."""
        data = {
            "summary": {
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2,
                "overall_score": 80.0
            },
            "note": "All tests completed"
        }

        lines = render_backend_table("Test Backend", data)

        assert isinstance(lines, list)
        assert len(lines) > 0
        assert any("Test Backend" in line for line in lines)
        assert any("10" in line for line in lines)
        assert any("8" in line for line in lines)
        assert any("80.0%" in line for line in lines)

    def test_render_with_none_data(self):
        """Test rendering table with None data."""
        lines = render_backend_table("Missing Backend", None)

        assert isinstance(lines, list)
        assert any("unavailable" in line.lower() for line in lines)

    def test_render_with_empty_summary(self):
        """Test rendering table with empty summary."""
        data = {"summary": {}}

        lines = render_backend_table("Empty Backend", data)

        assert isinstance(lines, list)
        assert len(lines) > 0

    def test_render_with_note(self):
        """Test rendering table with note."""
        data = {
            "summary": {
                "total_tests": 5,
                "passed_tests": 5,
                "failed_tests": 0,
                "overall_score": 100.0
            },
            "note": "Perfect score!"
        }

        lines = render_backend_table("Backend with Note", data)

        assert any("Perfect score!" in line for line in lines)

    def test_render_without_note(self):
        """Test rendering table without note."""
        data = {
            "summary": {
                "total_tests": 5,
                "passed_tests": 5,
                "failed_tests": 0,
                "overall_score": 100.0
            }
        }

        lines = render_backend_table("Backend without Note", data)

        # Should still render successfully
        assert len(lines) > 0


class TestGenerateSummary:
    """Test summary generation."""

    def test_generate_with_both_backends(self):
        """Test generating summary with both backends."""
        ollama_data = {
            "summary": {
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2,
                "overall_score": 80.0
            }
        }

        direct_data = {
            "summary": {
                "total_tests": 15,
                "passed_tests": 14,
                "failed_tests": 1,
                "overall_score": 93.3
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write test files
            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            # Generate summary
            summary = generate_summary(ollama_path, direct_path)

            assert "Hybrid Benchmark Results" in summary
            assert "Ollama Backend" in summary
            assert "Direct API Backend" in summary
            assert "Combined Summary" in summary
            assert "25" in summary  # Total tests: 10 + 15
            assert "22" in summary  # Total passed: 8 + 14

    def test_generate_with_missing_ollama(self):
        """Test generating summary with missing Ollama data."""
        direct_data = {
            "summary": {
                "total_tests": 10,
                "passed_tests": 10,
                "failed_tests": 0,
                "overall_score": 100.0
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "missing.json"
            direct_path = tmpdir_path / "direct.json"
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path)

            assert "unavailable" in summary.lower()
            assert "Direct API Backend" in summary

    def test_generate_with_output_file(self):
        """Test generating summary with output file."""
        ollama_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"
            output_path = tmpdir_path / "summary.md"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path, output_path)

            assert output_path.exists()
            assert output_path.read_text() == summary

    def test_generate_includes_timestamp(self):
        """Test that generated summary includes timestamp."""
        ollama_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path)

            assert "Generated:" in summary

    def test_generate_includes_apex_compliance(self):
        """Test that generated summary includes APEX compliance note."""
        ollama_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path)

            assert "APEX Security Framework" in summary
            assert "No PII logged" in summary


class TestCombinedSummary:
    """Test combined summary calculations."""

    def test_combined_summary_calculations(self):
        """Test combined summary calculates totals correctly."""
        ollama_data = {
            "summary": {
                "total_tests": 10,
                "passed_tests": 7,
                "failed_tests": 3,
                "overall_score": 70.0
            }
        }

        direct_data = {
            "summary": {
                "total_tests": 20,
                "passed_tests": 18,
                "failed_tests": 2,
                "overall_score": 90.0
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path)

            # Total tests: 10 + 20 = 30
            assert "30" in summary

            # Total passed: 7 + 18 = 25
            assert "25" in summary

            # Total failed: 3 + 2 = 5
            assert "5" in summary

            # Success rate: 25/30 = 83.3%
            assert "83.3%" in summary

    def test_combined_summary_with_zero_tests(self):
        """Test combined summary with zero tests."""
        ollama_data = {"summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "overall_score": 0.0}}
        direct_data = {"summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "overall_score": 0.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "ollama.json"
            direct_path = tmpdir_path / "direct.json"

            ollama_path.write_text(json.dumps(ollama_data))
            direct_path.write_text(json.dumps(direct_data))

            summary = generate_summary(ollama_path, direct_path)

            # Should handle division by zero gracefully
            assert "0.0%" in summary or "nan" not in summary.lower()


class TestMainFunction:
    """Test main CLI function."""

    def test_main_with_flat_structure(self):
        """Test main with flat directory structure."""
        ollama_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Flat structure
            (tmpdir_path / "ollama_report.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "direct_report.json").write_text(json.dumps(direct_data))

            with patch('sys.argv', ['script', str(tmpdir_path)]):
                exit_code = main()

            assert exit_code == 0

    def test_main_with_nested_structure(self):
        """Test main with nested directory structure."""
        ollama_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 5, "passed_tests": 5, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Nested structure
            (tmpdir_path / "ollama").mkdir()
            (tmpdir_path / "direct").mkdir()

            (tmpdir_path / "ollama" / "ollama_report.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "direct" / "direct_report.json").write_text(json.dumps(direct_data))

            with patch('sys.argv', ['script', str(tmpdir_path)]):
                exit_code = main()

            assert exit_code == 0

    def test_main_with_output_file(self):
        """Test main with output file specified."""
        ollama_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "ollama_report.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "direct_report.json").write_text(json.dumps(direct_data))

            output_file = tmpdir_path / "output.md"

            with patch('sys.argv', ['script', str(tmpdir_path), '--output', str(output_file)]):
                exit_code = main()

            assert exit_code == 0
            assert output_file.exists()

    def test_main_with_custom_filenames(self):
        """Test main with custom filenames."""
        ollama_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "custom_ollama.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "custom_direct.json").write_text(json.dumps(direct_data))

            with patch('sys.argv', [
                'script',
                str(tmpdir_path),
                '--ollama-file', 'custom_ollama.json',
                '--direct-file', 'custom_direct.json'
            ]):
                exit_code = main()

            assert exit_code == 0

    def test_main_with_github_step_summary(self):
        """Test main with GITHUB_STEP_SUMMARY env var."""
        ollama_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 1, "passed_tests": 1, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "ollama_report.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "direct_report.json").write_text(json.dumps(direct_data))

            github_summary = tmpdir_path / "github_summary.md"

            with patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': str(github_summary)}):
                with patch('sys.argv', ['script', str(tmpdir_path)]):
                    exit_code = main()

            assert exit_code == 0
            assert github_summary.exists()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_render_table_with_missing_fields(self):
        """Test rendering table with missing summary fields."""
        data = {
            "summary": {
                "total_tests": 10
                # Missing other fields
            }
        }

        lines = render_backend_table("Incomplete Backend", data)

        # Should handle missing fields gracefully
        assert len(lines) > 0
        assert any("10" in line for line in lines)

    def test_generate_summary_both_missing(self):
        """Test generating summary when both backends are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            ollama_path = tmpdir_path / "missing1.json"
            direct_path = tmpdir_path / "missing2.json"

            summary = generate_summary(ollama_path, direct_path)

            # Should still generate a summary
            assert "Hybrid Benchmark Results" in summary
            assert "unavailable" in summary.lower()

    def test_load_json_with_unicode(self):
        """Test loading JSON with unicode characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({"message": "Test with emoji 🚀 and unicode é"}, f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result is not None
            assert "emoji" in result["message"]
        finally:
            temp_path.unlink()

    def test_success_rate_calculation_edge_cases(self):
        """Test success rate calculation with edge cases."""
        # All pass
        ollama_data = {"summary": {"total_tests": 10, "passed_tests": 10, "failed_tests": 0, "overall_score": 100.0}}
        direct_data = {"summary": {"total_tests": 10, "passed_tests": 10, "failed_tests": 0, "overall_score": 100.0}}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "ollama.json").write_text(json.dumps(ollama_data))
            (tmpdir_path / "direct.json").write_text(json.dumps(direct_data))

            summary = generate_summary(
                tmpdir_path / "ollama.json",
                tmpdir_path / "direct.json"
            )

            assert "100.0%" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])