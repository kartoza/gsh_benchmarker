#!/usr/bin/env python3
"""
Test script to verify the original NameError has been fixed
"""

import unittest
import sys
from unittest.mock import patch, Mock


class TestOriginalErrorScenario(unittest.TestCase):
    """Test cases for the original NameError fix"""

    def test_original_error_scenario(self):
        """Test the exact scenario that was causing the NameError"""
        
        print("Testing the original error scenario...")
        
        try:
            # Import the modules
            from gsh_benchmarker.geoserver.core import GeoServerTester
            from gsh_benchmarker.geoserver.capabilities import LayerInfo
            
            # Create tester instance
            tester = GeoServerTester()
            tester.server_url = "http://test.example.com"
            tester._setup_urls()
            
            # Set up a mock layer like the UI would do after discovery
            mock_layer = LayerInfo(
                name="bkb_2024",
                title="BKB 2024",
                abstract="Test layer",
                srs_list=["EPSG:3857"],
                bbox={'minx': 0, 'miny': 0, 'maxx': 100, 'maxy': 100}
            )
            
            tester.layers = {"bkb_2024": mock_layer}
            
            print("✅ Setup complete - no NameError")
            
            # Mock subprocess to avoid actual Apache Bench call
            with patch('gsh_benchmarker.geoserver.core.subprocess.run') as mock_subprocess, \
                 patch('builtins.open'), \
                 patch('pathlib.Path.mkdir'):
                
                # Mock successful Apache Bench result
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
                
                # This is the exact call that was failing before
                result = tester.run_single_test("bkb_2024", 100, 5000)
                
                print("✅ run_single_test completed successfully - no NameError")
                print(f"✅ Test result created: {result is not None}")
                
                self.assertTrue(True, "Original NameError has been fixed!")
                
        except NameError as e:
            self.fail(f"NameError still exists: {e}")
        except Exception as e:
            self.fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    unittest.main()