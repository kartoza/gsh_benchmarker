"""
WMS GetCapabilities parsing and layer discovery functionality
"""

import xml.etree.ElementTree as ET
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import KARTOZA_COLORS, REQUEST_TIMEOUT

console = Console()

@dataclass
class LayerInfo:
    """Container for layer information from WMS capabilities"""
    name: str
    title: str
    abstract: str = ""
    keywords: List[str] = None
    bbox: Optional[Dict[str, float]] = None
    srs_list: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.srs_list is None:
            self.srs_list = []

class CapabilitiesParser:
    """Parser for WMS GetCapabilities responses"""
    
    # Common XML namespaces used in WMS capabilities
    NAMESPACES = {
        'wms': 'http://www.opengis.net/wms',
        'ogc': 'http://www.opengis.net/ogc',
        'xlink': 'http://www.w3.org/1999/xlink'
    }
    
    def __init__(self, base_url: str):
        """Initialize with base GeoServer URL"""
        self.base_url = base_url.rstrip('/')
        self.wms_url = f"{self.base_url}/wms"
        self.wmts_url = f"{self.base_url}/gwc/service/wmts"
        
    def get_capabilities(self) -> Optional[ET.Element]:
        """Fetch and parse WMS GetCapabilities response"""
        
        capabilities_url = f"{self.wms_url}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
        
        try:
            with console.status(f"[{KARTOZA_COLORS['highlight2']}]Fetching WMS capabilities..."):
                response = requests.get(capabilities_url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                return root
                
        except requests.RequestException as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to fetch capabilities: {e}[/]")
            return None
        except ET.ParseError as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to parse capabilities XML: {e}[/]")
            return None
    
    def parse_layers(self, capabilities_root: ET.Element) -> List[LayerInfo]:
        """Parse layer information from capabilities XML"""
        
        layers = []
        
        # Try different XPath expressions for different WMS versions
        layer_xpaths = [
            './/wms:Layer/wms:Layer',  # WMS 1.3.0
            './/Layer/Layer',         # No namespace
            './/wms:Layer[wms:Name]', # Direct named layers
            './/Layer[Name]'          # No namespace named layers
        ]
        
        layer_elements = []
        for xpath in layer_xpaths:
            try:
                elements = capabilities_root.findall(xpath, self.NAMESPACES)
                if elements:
                    layer_elements = elements
                    break
            except Exception:
                continue
        
        # Fallback: find all Layer elements with Name children
        if not layer_elements:
            for layer_elem in capabilities_root.iter():
                if (layer_elem.tag.endswith('Layer') and 
                    any(child.tag.endswith('Name') for child in layer_elem)):
                    layer_elements.append(layer_elem)
        
        for layer_elem in layer_elements:
            layer_info = self._parse_single_layer(layer_elem)
            if layer_info and layer_info.name:
                layers.append(layer_info)
        
        return layers
    
    def _parse_single_layer(self, layer_elem: ET.Element) -> Optional[LayerInfo]:
        """Parse a single layer element"""
        
        try:
            # Extract name (required)
            name_elem = self._find_child(layer_elem, ['Name', 'wms:Name'])
            if name_elem is None or not name_elem.text:
                return None
            
            name = name_elem.text.strip()
            
            # Extract title
            title_elem = self._find_child(layer_elem, ['Title', 'wms:Title'])
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else name
            
            # Extract abstract
            abstract_elem = self._find_child(layer_elem, ['Abstract', 'wms:Abstract'])
            abstract = abstract_elem.text.strip() if abstract_elem is not None and abstract_elem.text else ""
            
            # Extract keywords
            keywords = []
            for keyword_elem in layer_elem.findall('.//wms:Keyword', self.NAMESPACES):
                if keyword_elem.text:
                    keywords.append(keyword_elem.text.strip())
            
            # Also try without namespace
            for keyword_elem in layer_elem.findall('.//Keyword'):
                if keyword_elem.text:
                    keywords.append(keyword_elem.text.strip())
            
            # Extract SRS/CRS information
            srs_list = []
            for srs_elem in layer_elem.findall('.//wms:SRS', self.NAMESPACES):
                if srs_elem.text:
                    srs_list.append(srs_elem.text.strip())
            
            for crs_elem in layer_elem.findall('.//wms:CRS', self.NAMESPACES):
                if crs_elem.text:
                    srs_list.append(crs_elem.text.strip())
            
            # Extract bounding box
            bbox = self._parse_bbox(layer_elem)
            
            return LayerInfo(
                name=name,
                title=title,
                abstract=abstract,
                keywords=keywords,
                bbox=bbox,
                srs_list=srs_list
            )
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]Warning: Failed to parse layer: {e}[/]")
            return None
    
    def _find_child(self, parent: ET.Element, tag_names: List[str]) -> Optional[ET.Element]:
        """Find child element with any of the given tag names"""
        for tag_name in tag_names:
            child = parent.find(tag_name, self.NAMESPACES)
            if child is None:
                child = parent.find(tag_name)  # Try without namespace
            if child is not None:
                return child
        return None
    
    def _parse_bbox(self, layer_elem: ET.Element) -> Optional[Dict[str, float]]:
        """Parse bounding box from layer element"""
        
        # Try different bbox formats
        bbox_xpaths = [
            './/wms:EX_GeographicBoundingBox',
            './/EX_GeographicBoundingBox', 
            './/wms:LatLonBoundingBox',
            './/LatLonBoundingBox',
            './/wms:BoundingBox[@SRS="EPSG:4326"]',
            './/BoundingBox[@SRS="EPSG:4326"]'
        ]
        
        for xpath in bbox_xpaths:
            bbox_elem = layer_elem.find(xpath, self.NAMESPACES)
            if bbox_elem is None:
                bbox_elem = layer_elem.find(xpath)
            
            if bbox_elem is not None:
                try:
                    if 'EX_GeographicBoundingBox' in xpath:
                        # WMS 1.3.0 format
                        west = self._get_bbox_value(bbox_elem, ['wms:westBoundLongitude', 'westBoundLongitude'])
                        east = self._get_bbox_value(bbox_elem, ['wms:eastBoundLongitude', 'eastBoundLongitude'])
                        south = self._get_bbox_value(bbox_elem, ['wms:southBoundLatitude', 'southBoundLatitude'])
                        north = self._get_bbox_value(bbox_elem, ['wms:northBoundLatitude', 'northBoundLatitude'])
                    else:
                        # Attribute format
                        west = float(bbox_elem.get('minx', bbox_elem.get('miny', 0)))
                        east = float(bbox_elem.get('maxx', bbox_elem.get('maxy', 0)))
                        south = float(bbox_elem.get('miny', bbox_elem.get('minx', 0)))
                        north = float(bbox_elem.get('maxy', bbox_elem.get('maxx', 0)))
                    
                    if all(v is not None for v in [west, east, south, north]):
                        return {
                            'minx': west,
                            'miny': south,
                            'maxx': east,
                            'maxy': north
                        }
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _get_bbox_value(self, bbox_elem: ET.Element, tag_names: List[str]) -> Optional[float]:
        """Get bounding box value from element"""
        for tag_name in tag_names:
            elem = bbox_elem.find(tag_name, self.NAMESPACES)
            if elem is None:
                elem = bbox_elem.find(tag_name)
            if elem is not None and elem.text:
                try:
                    return float(elem.text.strip())
                except ValueError:
                    continue
        return None
    
    def get_service_info(self, capabilities_root: ET.Element) -> Dict[str, str]:
        """Extract service information from capabilities"""
        
        service_info = {}
        
        # Find service element
        service_elem = capabilities_root.find('.//wms:Service', self.NAMESPACES)
        if service_elem is None:
            service_elem = capabilities_root.find('.//Service')
        
        if service_elem is not None:
            # Extract service metadata
            for field_name, tag_names in [
                ('title', ['wms:Title', 'Title']),
                ('abstract', ['wms:Abstract', 'Abstract']),
                ('version', ['wms:Version', 'Version']),
                ('name', ['wms:Name', 'Name'])
            ]:
                elem = self._find_child(service_elem, tag_names)
                if elem is not None and elem.text:
                    service_info[field_name] = elem.text.strip()
        
        return service_info
    
    def test_layer_access(self, layer_name: str) -> Tuple[bool, int]:
        """Test if a specific layer is accessible via WMTS"""
        
        # Generate a simple tile request
        tile_url = (f"{self.wmts_url}?"
                   f"SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&"
                   f"LAYER={layer_name}&STYLE=&"
                   f"TILEMATRIXSET=WebMercatorQuad&"
                   f"TILEMATRIX=5&TILEROW=10&TILECOL=16&"
                   f"FORMAT=image/png")
        
        try:
            response = requests.get(tile_url, timeout=REQUEST_TIMEOUT)
            return response.status_code == 200, response.status_code
        except requests.RequestException:
            return False, 0

def discover_layers(base_url: str) -> Tuple[List[LayerInfo], Dict[str, str]]:
    """Discover layers from a GeoServer instance"""
    
    parser = CapabilitiesParser(base_url)
    
    # Get capabilities
    capabilities_root = parser.get_capabilities()
    if capabilities_root is None:
        return [], {}
    
    # Parse layers and service info
    layers = parser.parse_layers(capabilities_root)
    service_info = parser.get_service_info(capabilities_root)
    
    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Discovered {len(layers)} layers[/]")
    
    return layers, service_info