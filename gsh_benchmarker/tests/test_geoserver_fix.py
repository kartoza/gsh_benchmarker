"""
Unit tests to verify the LAYERS variable fix in the GeoServer testing suite
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from geoserver_tests.core import GeoServerTester, TestResult
from geoserver_tests.capabilities import LayerInfo


class TestGeoServerFix(unittest.TestCase):
    """Test cases to verify the LAYERS variable fix"""

    def setUp(self):
        """Set up test fixtures"""
        self.tester = GeoServerTester()
        
        # Mock layer info
        self.mock_layer = LayerInfo(
            name="test_layer",
            title="Test Layer",
            abstract="A test layer for unit testing",
            srs_list=["EPSG:3857", "EPSG:4326"],
            bbox={'minx': 0, 'miny': 0, 'maxx': 100, 'maxy': 100}
        )
        
        # Set up mock layers dictionary
        self.tester.layers = {
            "test_layer": self.mock_layer,
            "another_layer": LayerInfo(
                name="another_layer",
                title="Another Layer", 
                abstract="Another test layer",
                srs_list=["EPSG:3857"],
                bbox={'minx': 50, 'miny': 50, 'maxx': 150, 'maxy': 150}
            )
        }
        
        self.tester.server_url = "http://test.example.com"
        self.tester._setup_urls()  # Initialize WMTS and WMS URLs

    def test_imports_work(self):
        """Test that all modules can be imported without NameError"""
        try:
            from geoserver_tests.core import GeoServerTester
            from geoserver_tests.ui import MenuInterface
            from geoserver_tests.capabilities import LayerInfo
        except NameError as e:
            self.fail(f"NameError during imports: {e}")

    def test_instantiation_works(self):
        """Test that classes can be instantiated without NameError"""
        try:
            tester = GeoServerTester()
            self.assertIsInstance(tester, GeoServerTester)
        except NameError as e:
            self.fail(f"NameError during instantiation: {e}")

    @patch('geoserver_tests.core.subprocess.run')
    def test_run_single_test_uses_self_layers(self, mock_subprocess):
        """Test that run_single_test uses self.layers instead of undefined LAYERS"""
        # Mock subprocess.run to simulate successful Apache Bench
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
        Requests per second:    100.50 [#/sec] (mean)
        Time per request:       9.95 [ms] (mean)
        Failed requests:        0
        Time taken for tests:   49.75 seconds
        Transfer rate:          1500.25 [Kbytes/sec] received
        """
        mock_subprocess.return_value = mock_result
        
        # Mock directory creation
        with patch.object(Path, 'mkdir'), \
             patch('builtins.open', unittest.mock.mock_open()):
            
            result = self.tester.run_single_test(
                layer_key="test_layer",
                concurrency=10,
                total_requests=100
            )
            
            # Verify test result was created successfully
            self.assertIsInstance(result, TestResult)
            self.assertEqual(result.layer, "test_layer")
            self.assertEqual(result.concurrency, 10)
            self.assertEqual(result.total_requests, 100)

    def test_get_layer_list_uses_self_layers(self):
        """Test that get_layer_list uses self.layers"""
        layer_list = self.tester.get_layer_list()
        
        self.assertIn("test_layer", layer_list)
        self.assertIn("another_layer", layer_list)
        self.assertEqual(len(layer_list), 2)

    def test_get_layer_info_uses_self_layers(self):
        """Test that get_layer_info uses self.layers"""
        layer_info = self.tester.get_layer_info("test_layer")
        
        self.assertIsNotNone(layer_info)
        self.assertEqual(layer_info.title, "Test Layer")
        self.assertEqual(layer_info.name, "test_layer")

    @patch('geoserver_tests.core.subprocess.run')
    def test_comprehensive_test_uses_self_layers(self, mock_subprocess):
        """Test that run_comprehensive_test uses self.layers instead of undefined LAYERS"""
        # Mock subprocess.run to simulate successful Apache Bench
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
        Requests per second:    50.25 [#/sec] (mean)
        Time per request:       19.90 [ms] (mean)
        Failed requests:        0
        Time taken for tests:   99.50 seconds
        Transfer rate:          750.75 [Kbytes/sec] received
        """
        mock_subprocess.return_value = mock_result
        
        # Mock directory operations and file I/O
        with patch.object(Path, 'mkdir'), \
             patch.object(Path, 'exists', return_value=True), \
             patch('shutil.rmtree'), \
             patch('builtins.open', unittest.mock.mock_open()), \
             patch.object(self.tester, 'test_connectivity', return_value=(True, 200)):
            
            results = self.tester.run_comprehensive_test(
                total_requests=100,
                concurrency_levels=[5, 10]
            )
            
            # Should have 4 results (2 layers × 2 concurrency levels)
            self.assertEqual(len(results), 4)
            
            # Verify all results are TestResult objects
            for result in results:
                self.assertIsInstance(result, TestResult)

    @patch('builtins.open', unittest.mock.mock_open())
    def test_save_test_metadata_uses_layer_info_object(self):
        """Test that _save_test_metadata correctly accesses LayerInfo object attributes"""
        # Create a test result
        result = TestResult(
            layer="test_layer",
            concurrency=10,
            total_requests=100,
            requests_per_second=50.0,
            mean_response_time=20.0,
            failed_requests=0,
            total_time=2.0,
            transfer_rate=1000.0,
            success_rate=100.0,
            test_id="test_123",
            timestamp="20241114_120000"
        )
        
        tile_url = "http://test.example.com/wmts?..."
        
        # Mock directory creation
        with patch.object(Path, 'mkdir'):
            # This should not raise any AttributeError about dict access
            try:
                self.tester._save_test_metadata(result, tile_url, self.mock_layer)
            except AttributeError as e:
                if "'LayerInfo' object" in str(e):
                    self.fail(f"LayerInfo object access error: {e}")

    def test_results_summary_uses_self_layers(self):
        """Test that get_results_summary uses self.layers correctly"""
        # Mock JSON files in results directory
        mock_json_data = {
            "layer": "test_layer",
            "concurrency_level": 10,
            "results": {
                "requests_per_second": "50.25",
                "mean_response_time_ms": "20.00",
                "failed_requests": "0",
                "success_rate": "100.0"
            }
        }
        
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'glob', return_value=[Path('test_result.json')]), \
             patch.object(Path, 'stat') as mock_stat, \
             patch('builtins.open', unittest.mock.mock_open(read_data='')) as mock_open, \
             patch('json.load', return_value=mock_json_data):
            
            mock_stat.return_value.st_mtime = datetime.now().timestamp()
            
            try:
                summary = self.tester.get_results_summary()
                # Should not raise NameError about LAYERS
                self.assertIsNotNone(summary)
            except NameError as e:
                if "LAYERS" in str(e):
                    self.fail(f"NameError about LAYERS: {e}")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)