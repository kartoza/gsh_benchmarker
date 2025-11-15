"""
Shared image rendering utilities for GSH Benchmarker Suite

Provides terminal image rendering capabilities that can be used across
all benchmarker implementations for previews, charts, and visualizations.
"""

import os
import base64
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from rich.console import Console
from rich.panel import Panel

from .colors import KARTOZA_COLORS
from .config import TEMP_DIR

console = Console()


class TerminalImageRenderer:
    """Handle rendering images in terminal using various methods"""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)
        self.terminal_type = self._detect_terminal_type()
        self.available_renderers = self._detect_available_renderers()
    
    def _detect_terminal_type(self) -> str:
        """Detect the type of terminal we're running in"""
        term = os.environ.get('TERM', '').lower()
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        
        # Check for Kitty terminal
        if 'kitty' in term or term_program == 'kitty':
            return 'kitty'
        elif 'xterm-kitty' in term:
            return 'kitty'
        # Check for iTerm2
        elif term_program == 'iterm.app':
            return 'iterm2'
        # Check for other terminals that support images
        elif any(x in term for x in ['xterm', 'screen', 'tmux']):
            return 'xterm-compatible'
        else:
            return 'generic'
    
    def _detect_available_renderers(self) -> list:
        """Detect which image rendering tools are available"""
        renderers = []
        
        # Check for chafa
        if shutil.which('chafa'):
            renderers.append('chafa')
        
        # Check for img2txt (from caca-utils)
        if shutil.which('img2txt'):
            renderers.append('img2txt')
        
        # Check for terminal image protocols
        if self.terminal_type in ['kitty', 'iterm2']:
            renderers.append(f'{self.terminal_type}_protocol')
        
        return renderers
    
    def get_terminal_info(self) -> Dict[str, Any]:
        """Get information about terminal capabilities"""
        return {
            'terminal_type': self.terminal_type,
            'available_renderers': self.available_renderers,
            'can_display_images': len(self.available_renderers) > 0,
            'recommended_renderer': self.available_renderers[0] if self.available_renderers else None
        }
    
    def render_image(
        self, 
        image_path: Path, 
        width: Optional[int] = None,
        height: Optional[int] = None,
        renderer: Optional[str] = None
    ) -> bool:
        """
        Render an image in the terminal
        
        Args:
            image_path: Path to the image file
            width: Desired width in characters/pixels
            height: Desired height in characters/pixels
            renderer: Specific renderer to use
            
        Returns:
            True if image was rendered successfully
        """
        if not image_path.exists():
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Image not found: {image_path}[/]")
            return False
        
        if not self.available_renderers:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No image renderers available[/]")
            return False
        
        # Choose renderer
        if renderer and renderer in self.available_renderers:
            chosen_renderer = renderer
        else:
            chosen_renderer = self.available_renderers[0]
        
        try:
            return self._render_with_method(image_path, chosen_renderer, width, height)
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to render image: {e}[/]")
            return False
    
    def _render_with_method(
        self, 
        image_path: Path, 
        method: str,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> bool:
        """Render image using specific method"""
        
        if method == 'chafa':
            return self._render_with_chafa(image_path, width, height)
        elif method == 'img2txt':
            return self._render_with_img2txt(image_path, width, height)
        elif method == 'kitty_protocol':
            return self._render_with_kitty(image_path)
        elif method == 'iterm2_protocol':
            return self._render_with_iterm2(image_path)
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Unknown renderer: {method}[/]")
            return False
    
    def _render_with_chafa(self, image_path: Path, width: Optional[int], height: Optional[int]) -> bool:
        """Render image using chafa"""
        cmd = ['chafa']
        
        if width and height:
            cmd.extend(['--size', f'{width}x{height}'])
        elif width:
            cmd.extend(['--size', f'{width}x'])
        elif height:
            cmd.extend(['--size', f'x{height}'])
        
        # Add color and animation options
        cmd.extend([
            '--colors', '256',
            '--format', 'symbols',
            str(image_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print(result.stdout)
                return True
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ chafa error: {result.stderr}[/]")
                return False
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ chafa failed: {e}[/]")
            return False
    
    def _render_with_img2txt(self, image_path: Path, width: Optional[int], height: Optional[int]) -> bool:
        """Render image using img2txt"""
        cmd = ['img2txt']
        
        if width:
            cmd.extend(['-W', str(width)])
        if height:
            cmd.extend(['-H', str(height)])
        
        cmd.append(str(image_path))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print(result.stdout)
                return True
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ img2txt error: {result.stderr}[/]")
                return False
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ img2txt failed: {e}[/]")
            return False
    
    def _render_with_kitty(self, image_path: Path) -> bool:
        """Render image using Kitty terminal graphics protocol"""
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
            
            # Kitty graphics protocol
            print(f'\033_Gf=100,a=T,m=1;{image_data}\033\\')
            print('\033_Ga=p,q=2\033\\')
            return True
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Kitty protocol failed: {e}[/]")
            return False
    
    def _render_with_iterm2(self, image_path: Path) -> bool:
        """Render image using iTerm2 inline images protocol"""
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
            
            # iTerm2 protocol
            print(f'\033]1337;File=inline=1;width=auto;height=auto:{image_data}\007')
            return True
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ iTerm2 protocol failed: {e}[/]")
            return False
    
    def create_terminal_preview(
        self, 
        image_path: Path,
        title: str = "Preview",
        max_width: int = 80,
        max_height: int = 24
    ) -> bool:
        """Create a terminal preview with rich formatting"""
        
        if not self.available_renderers:
            # Fallback: show file info
            file_size = image_path.stat().st_size
            console.print(Panel(
                f"📷 {image_path.name}\n"
                f"Size: {file_size:,} bytes\n"
                f"Path: {image_path}\n\n"
                f"[{KARTOZA_COLORS['highlight3']}]No terminal image renderers available[/]",
                title=title,
                border_style=KARTOZA_COLORS['highlight3']
            ))
            return False
        
        # Show image with border
        console.print(Panel(
            f"[{KARTOZA_COLORS['highlight2']}]Rendering with {self.available_renderers[0]}...[/]",
            title=title,
            border_style=KARTOZA_COLORS['highlight4']
        ))
        
        return self.render_image(image_path, max_width, max_height)


def download_preview_image(
    url: str, 
    output_path: Path,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    Download a preview image from URL
    
    Args:
        url: Image URL to download
        output_path: Where to save the image  
        timeout: Request timeout in seconds
        headers: Optional HTTP headers
        
    Returns:
        True if download was successful
    """
    try:
        import requests
        
        response = requests.get(url, timeout=timeout, headers=headers or {})
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Downloaded: {output_path}[/]")
        return True
        
    except Exception as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to download image: {e}[/]")
        return False


def create_simple_chart_ascii(
    data: Dict[str, float],
    title: str = "Chart",
    width: int = 50,
    bar_char: str = "█"
) -> str:
    """
    Create a simple ASCII bar chart
    
    Args:
        data: Dictionary of label -> value pairs
        title: Chart title
        width: Maximum width of bars
        bar_char: Character to use for bars
        
    Returns:
        ASCII chart as string
    """
    if not data:
        return f"{title}: No data"
    
    max_val = max(data.values())
    if max_val == 0:
        return f"{title}: All values are zero"
    
    chart_lines = [f"\n{title}", "=" * len(title)]
    
    for label, value in data.items():
        bar_length = int((value / max_val) * width)
        bar = bar_char * bar_length
        chart_lines.append(f"{label:15} │{bar:<{width}} {value:.1f}")
    
    return "\n".join(chart_lines)