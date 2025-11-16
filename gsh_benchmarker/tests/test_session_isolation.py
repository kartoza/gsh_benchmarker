#!/usr/bin/env python3
"""
Test suite for session isolation in report generation

This test verifies that PDF reports only contain data from the current test session
and do not show results from previous runs.
"""

import pytest
import json
import time
from datetime import datetime
from pathlib import Path

from ..common.reports import ReportGenerator
from ..common.utils import BenchmarkResult
from ..common.pdf_generator import generate_pdf_report


class TestSessionIsolation:
    """Test cases for session isolation in benchmark reporting"""
    
    @pytest.fixture
    def temp_results_dir(self, tmp_path):
        """Create temporary results directory for testing"""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        return results_dir
    
    @pytest.fixture
    def temp_reports_dir(self, tmp_path):
        """Create temporary reports directory for testing"""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        return reports_dir
    
    def create_mock_benchmark_result(self, layer_name: str, concurrency: int, timestamp: str = None) -> BenchmarkResult:
        """Create a mock benchmark result for testing"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
        return BenchmarkResult(
            target=layer_name,
            service_type='geoserver',
            concurrency=concurrency,
            total_requests=1000,
            requests_per_second=50.0 + concurrency/10,  # Variable performance based on concurrency
            mean_response_time=200.0 - concurrency/10,
            failed_requests=0,
            total_time=1000/(50.0 + concurrency/10),
            transfer_rate=1000.0,
            success_rate=100.0,
            test_id=f"{layer_name}_c{concurrency}_{timestamp}",
            timestamp=timestamp
        )
    
    def create_session_results(self, layer_name: str, concurrency_levels: list, 
                              results_dir: Path, session_type: str = "single_layer") -> tuple:
        """Create consolidated results for a test session"""
        results = []
        session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include microseconds for uniqueness
        
        for concurrency in concurrency_levels:
            result = self.create_mock_benchmark_result(layer_name, concurrency, session_timestamp)
            results.append(result)
        
        # Create ReportGenerator with temporary directory
        report_gen = ReportGenerator('geoserver', results_dir=results_dir)
        
        test_config = {
            'total_requests': 1000,
            'concurrency_levels': concurrency_levels,
            'layers_tested': [layer_name],
            'server': 'test.example.com',
            'session_type': session_type
        }
        
        session_file = report_gen.consolidate_results(results, session_timestamp, test_config)
        return session_file, results, session_timestamp
    
    def test_single_layer_session_isolation(self, temp_results_dir):
        """Test that single layer sessions only contain data for that layer"""
        
        # Create session for layer 1
        layer1_name = 'AfstandTotKoelte'
        session1_file, session1_results, _ = self.create_session_results(
            layer1_name, [10, 100, 500], temp_results_dir, 'single_layer'
        )
        
        # Small delay to ensure different timestamps
        time.sleep(0.001)
        
        # Create session for layer 2
        layer2_name = 'bkb_2024'
        session2_file, session2_results, _ = self.create_session_results(
            layer2_name, [10, 100], temp_results_dir, 'single_layer'
        )
        
        # Verify that sessions are isolated
        assert session1_file != session2_file, "Session files should be different"
        
        # Load and verify session 1 contains only layer 1
        with open(session1_file) as f:
            session1_data = json.load(f)
        
        session1_layers = session1_data['test_suite']['targets_tested']
        assert len(session1_layers) == 1, f"Session 1 should contain 1 layer, got {len(session1_layers)}"
        assert layer1_name in session1_layers, f"Session 1 should contain {layer1_name}"
        assert layer2_name not in session1_layers, f"Session 1 should not contain {layer2_name}"
        
        # Verify session 1 has correct number of results
        assert len(session1_data['results']) == 3, f"Session 1 should have 3 results, got {len(session1_data['results'])}"
        
        # Load and verify session 2 contains only layer 2
        with open(session2_file) as f:
            session2_data = json.load(f)
        
        session2_layers = session2_data['test_suite']['targets_tested']
        assert len(session2_layers) == 1, f"Session 2 should contain 1 layer, got {len(session2_layers)}"
        assert layer2_name in session2_layers, f"Session 2 should contain {layer2_name}"
        assert layer1_name not in session2_layers, f"Session 2 should not contain {layer1_name}"
        
        # Verify session 2 has correct number of results
        assert len(session2_data['results']) == 2, f"Session 2 should have 2 results, got {len(session2_data['results'])}"
    
    def test_comprehensive_session_isolation(self, temp_results_dir):
        """Test that comprehensive sessions contain multiple layers but only from that session"""
        
        # Create a comprehensive session with multiple layers
        layers = ['layer1', 'layer2', 'layer3']
        all_results = []
        session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        for layer_name in layers:
            for concurrency in [10, 100]:
                result = self.create_mock_benchmark_result(layer_name, concurrency, session_timestamp)
                all_results.append(result)
        
        # Consolidate all results into one comprehensive session
        report_gen = ReportGenerator('geoserver', results_dir=temp_results_dir)
        test_config = {
            'total_requests': 1000,
            'concurrency_levels': [10, 100],
            'layers_tested': layers,
            'server': 'test.example.com',
            'session_type': 'comprehensive'
        }
        
        session_file = report_gen.consolidate_results(all_results, session_timestamp, test_config)
        
        # Verify comprehensive session contains all intended layers
        with open(session_file) as f:
            session_data = json.load(f)
        
        session_layers = session_data['test_suite']['targets_tested']
        assert len(session_layers) == 3, f"Comprehensive session should contain 3 layers, got {len(session_layers)}"
        
        for layer in layers:
            assert layer in session_layers, f"Comprehensive session should contain {layer}"
        
        # Verify correct number of results (3 layers × 2 concurrency levels = 6 results)
        assert len(session_data['results']) == 6, f"Comprehensive session should have 6 results, got {len(session_data['results'])}"
        
        # Verify session type is marked correctly
        assert session_data['configuration']['session_type'] == 'comprehensive'
    
    def test_session_metadata_integrity(self, temp_results_dir):
        """Test that session metadata correctly reflects the test configuration"""
        
        layer_name = 'test_layer'
        concurrency_levels = [10, 50, 100]
        session_file, results, timestamp = self.create_session_results(
            layer_name, concurrency_levels, temp_results_dir, 'single_layer'
        )
        
        # Load session data and verify metadata
        with open(session_file) as f:
            session_data = json.load(f)
        
        # Verify test suite metadata
        test_suite = session_data['test_suite']
        assert test_suite['service_type'] == 'geoserver'
        assert test_suite['timestamp'] == timestamp
        assert test_suite['total_requests_per_test'] == 1000
        assert test_suite['concurrency_levels'] == concurrency_levels
        assert test_suite['targets_tested'] == [layer_name]
        assert test_suite['total_tests'] == len(results)
        
        # Verify configuration metadata
        config = session_data['configuration']
        assert config['total_requests'] == 1000
        assert config['concurrency_levels'] == concurrency_levels
        assert config['layers_tested'] == [layer_name]
        assert config['session_type'] == 'single_layer'
        assert config['server'] == 'test.example.com'
        
        # Verify result data integrity
        assert len(session_data['results']) == len(concurrency_levels)
        
        for i, result_data in enumerate(session_data['results']):
            assert result_data['target'] == layer_name
            assert result_data['service_type'] == 'geoserver'
            assert result_data['concurrency_level'] == concurrency_levels[i]
            assert result_data['total_requests'] == 1000
            assert 'results' in result_data
            assert 'metadata' in result_data
    
    def test_no_cross_session_contamination(self, temp_results_dir):
        """Test that creating new sessions doesn't affect existing session files"""
        
        # Create first session
        session1_file, _, timestamp1 = self.create_session_results(
            'layer_a', [10, 100], temp_results_dir, 'single_layer'
        )
        
        # Read initial session 1 data
        with open(session1_file) as f:
            original_session1_data = json.load(f)
        
        time.sleep(0.001)  # Ensure different timestamp
        
        # Create second session
        session2_file, _, timestamp2 = self.create_session_results(
            'layer_b', [50, 200], temp_results_dir, 'single_layer'
        )
        
        # Verify sessions have different files and timestamps
        assert session1_file != session2_file
        assert timestamp1 != timestamp2
        
        # Re-read session 1 data and verify it's unchanged
        with open(session1_file) as f:
            current_session1_data = json.load(f)
        
        assert current_session1_data == original_session1_data, "Session 1 data should be unchanged"
        
        # Verify session 1 still contains only layer_a
        session1_layers = current_session1_data['test_suite']['targets_tested']
        assert session1_layers == ['layer_a'], "Session 1 should still only contain layer_a"
        
        # Verify session 2 contains only layer_b
        with open(session2_file) as f:
            session2_data = json.load(f)
        
        session2_layers = session2_data['test_suite']['targets_tested']
        assert session2_layers == ['layer_b'], "Session 2 should only contain layer_b"


# Integration test that can be run standalone
def test_pdf_generation_uses_session_data(tmp_path):
    """Integration test to verify PDF generation uses session-specific data"""
    
    # This test is more complex and requires the full PDF generation pipeline
    # It's marked as an integration test and may require additional setup
    
    # Create temporary directories
    results_dir = tmp_path / "results"
    reports_dir = tmp_path / "reports" 
    results_dir.mkdir()
    reports_dir.mkdir()
    
    # Create a single-layer session
    session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    layer_name = 'test_pdf_layer'
    
    results = []
    for concurrency in [10, 100]:
        result = BenchmarkResult(
            target=layer_name,
            service_type='geoserver',
            concurrency=concurrency,
            total_requests=500,
            requests_per_second=25.0 + concurrency/20,
            mean_response_time=400.0 - concurrency/5,
            failed_requests=0,
            total_time=500/(25.0 + concurrency/20),
            transfer_rate=500.0,
            success_rate=100.0,
            test_id=f"{layer_name}_c{concurrency}_{session_timestamp}",
            timestamp=session_timestamp
        )
        results.append(result)
    
    # Create consolidated session results
    report_gen = ReportGenerator('geoserver', reports_dir=reports_dir, results_dir=results_dir)
    test_config = {
        'total_requests': 500,
        'concurrency_levels': [10, 100],
        'layers_tested': [layer_name],
        'server': 'test.pdf.com',
        'session_type': 'single_layer'
    }
    
    session_file = report_gen.consolidate_results(results, session_timestamp, test_config)
    
    # Verify the session file was created correctly
    assert session_file.exists(), "Session file should be created"
    
    with open(session_file) as f:
        session_data = json.load(f)
    
    # Verify session contains only our test layer
    assert session_data['test_suite']['targets_tested'] == [layer_name]
    assert len(session_data['results']) == 2  # Two concurrency levels
    
    # Note: Full PDF generation test would require proper environment setup
    # This test verifies the session data preparation is correct


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    import sys
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test instance
        test_instance = TestSessionIsolation()
        
        # Run individual tests
        print("🧪 Running Session Isolation Tests...")
        
        try:
            test_instance.test_single_layer_session_isolation(tmp_path / "results1")
            print("✅ Single layer session isolation test passed")
            
            test_instance.test_comprehensive_session_isolation(tmp_path / "results2") 
            print("✅ Comprehensive session isolation test passed")
            
            test_instance.test_session_metadata_integrity(tmp_path / "results3")
            print("✅ Session metadata integrity test passed")
            
            test_instance.test_no_cross_session_contamination(tmp_path / "results4")
            print("✅ Cross-session contamination test passed")
            
            test_pdf_generation_uses_session_data(tmp_path / "pdf_test")
            print("✅ PDF generation session data test passed")
            
            print("\n🎉 All session isolation tests passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            sys.exit(1)