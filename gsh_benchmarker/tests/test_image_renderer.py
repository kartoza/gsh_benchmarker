#!/usr/bin/env python3
"""
Test script for the enhanced image rendering functionality
"""

import unittest
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

from geoserver_tests.image_renderer import TerminalImageRenderer


class TestImageRenderer(unittest.TestCase):
    """Test cases for the enhanced image renderer"""

    def create_test_image(self, path: Path, width: int = 300, height: int = 200):
        """Create a test image for rendering"""
        # Create a simple test image with PIL
        img = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Draw some shapes
        draw.rectangle([50, 50, width-50, height-50], outline='darkblue', width=3)
        draw.ellipse([100, 75, width-100, height-75], fill='yellow', outline='orange', width=2)
        draw.text((width//2-50, height//2-10), "GeoServer", fill='black')
        
        img.save(path, 'PNG')


    def test_image_rendering_capabilities(self):
        """Test the image rendering capabilities detection"""
        renderer = TerminalImageRenderer()
        
        # Test capabilities detection
        caps = renderer.get_capabilities_info()
        self.assertIsInstance(caps, dict)
        self.assertIn('terminal_type', caps)
        self.assertIn('available_renderers', caps)
        self.assertIn('supports_true_images', caps)
        
        # Terminal type should be a string
        self.assertIsInstance(caps['terminal_type'], str)
        
        # Available renderers should be a list
        self.assertIsInstance(caps['available_renderers'], list)
        
        # Supports true images should be a boolean
        self.assertIsInstance(caps['supports_true_images'], bool)

    def test_image_rendering_functionality(self):
        """Test the image rendering functionality"""
        # Initialize renderer
        renderer = TerminalImageRenderer()
        
        # Create a test image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            test_image_path = Path(tmp_file.name)
        
        try:
            self.create_test_image(test_image_path)
            self.assertTrue(test_image_path.exists())
            self.assertGreater(test_image_path.stat().st_size, 0)
            
            # Test rendering - should not raise exceptions
            try:
                success = renderer.render_image(test_image_path, max_width=40, max_height=15)
                # Success depends on available renderers, but should not crash
                self.assertIsInstance(success, bool)
            except Exception as e:
                self.fail(f"Image rendering raised exception: {e}")
                
        finally:
            # Clean up
            if test_image_path.exists():
                test_image_path.unlink()

    def test_image_rendering_with_missing_file(self):
        """Test image rendering with non-existent file"""
        renderer = TerminalImageRenderer()
        
        # Test with non-existent file
        non_existent_path = Path("/tmp/does_not_exist.png")
        success = renderer.render_image(non_existent_path)
        self.assertFalse(success)

    def test_renderer_initialization(self):
        """Test that renderer initializes without errors"""
        try:
            renderer = TerminalImageRenderer()
            self.assertIsInstance(renderer, TerminalImageRenderer)
        except Exception as e:
            self.fail(f"TerminalImageRenderer initialization failed: {e}")


if __name__ == "__main__":
    unittest.main()