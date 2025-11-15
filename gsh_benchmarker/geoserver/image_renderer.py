"""
Enhanced image rendering for terminal display
Supports chafa and Kitty terminal image protocols
"""

import os
import base64
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console

console = Console()


class TerminalImageRenderer:
    """Handle rendering images in terminal using various methods"""
    
    def __init__(self):
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
        
        # Check for img2txt (from libcaca)
        if shutil.which('img2txt'):
            renderers.append('img2txt')
        
        # Check for jp2a (for JPEG to ASCII)
        if shutil.which('jp2a'):
            renderers.append('jp2a')
        
        # Kitty terminal support
        if self.terminal_type == 'kitty':
            renderers.append('kitty')
        
        # iTerm2 support
        if self.terminal_type == 'iterm2':
            renderers.append('iterm2')
        
        return renderers
    
    def render_image(self, image_path: Path, max_width: int = 80, max_height: int = 25) -> bool:
        """
        Render an image in the terminal using the best available method
        
        Args:
            image_path: Path to the image file
            max_width: Maximum width in characters
            max_height: Maximum height in characters
        
        Returns:
            True if image was successfully rendered, False otherwise
        """
        if not image_path.exists():
            console.print(f"[red]❌ Image file not found: {image_path}[/red]")
            return False
        
        # Try renderers in order of preference
        for renderer in self.available_renderers:
            if self._render_with_method(renderer, image_path, max_width, max_height):
                return True
        
        # Fallback message
        console.print(f"[yellow]📷 Image saved to: {image_path}[/yellow]")
        console.print(f"[dim]No terminal image renderer available. Install 'chafa' for better image display.[/dim]")
        return False
    
    def _render_with_method(self, method: str, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using a specific method"""
        try:
            if method == 'kitty':
                return self._render_kitty(image_path, max_width, max_height)
            elif method == 'iterm2':
                return self._render_iterm2(image_path, max_width, max_height)
            elif method == 'chafa':
                return self._render_chafa(image_path, max_width, max_height)
            elif method == 'img2txt':
                return self._render_img2txt(image_path, max_width, max_height)
            elif method == 'jp2a':
                return self._render_jp2a(image_path, max_width, max_height)
        except Exception as e:
            console.print(f"[dim]Failed to render with {method}: {e}[/dim]")
        
        return False
    
    def _render_kitty(self, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using Kitty terminal graphics protocol"""
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            encoded_data = base64.b64encode(image_data).decode('ascii')
            
            # Calculate display dimensions
            # Kitty uses character cells, so we need to be careful about sizing
            width_chars = min(max_width, 120)
            height_chars = min(max_height, 30)
            
            # Kitty graphics protocol
            # Format: \033_G<params>;<data>\033\
            params = f"a=T,f=100,s={width_chars},r={height_chars}"
            
            # Split data into chunks (Kitty has limits)
            chunk_size = 4096
            chunks = [encoded_data[i:i+chunk_size] for i in range(0, len(encoded_data), chunk_size)]
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    # First chunk
                    if len(chunks) == 1:
                        # Single chunk
                        print(f'\033_G{params};{chunk}\033\\')
                    else:
                        # First of multiple chunks
                        print(f'\033_G{params},m=1;{chunk}\033\\')
                elif i == len(chunks) - 1:
                    # Last chunk
                    print(f'\033_G,m=0;{chunk}\033\\')
                else:
                    # Middle chunk
                    print(f'\033_G,m=1;{chunk}\033\\')
            
            # Add some spacing
            print()
            return True
            
        except Exception as e:
            console.print(f"[dim]Kitty rendering failed: {e}[/dim]")
            return False
    
    def _render_iterm2(self, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using iTerm2 image protocol"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            encoded_data = base64.b64encode(image_data).decode('ascii')
            
            # iTerm2 inline image protocol
            # \033]1337;File=inline=1:<base64_data>\a
            print(f'\033]1337;File=inline=1;width={max_width}:{encoded_data}\a')
            print()
            return True
            
        except Exception:
            return False
    
    def _render_chafa(self, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using chafa"""
        try:
            # Enhanced chafa options for better quality
            cmd = [
                'chafa',
                '--size', f'{max_width}x{max_height}',
                '--format', 'symbols',  # Use Unicode symbols for better quality
                '--symbols', 'all',     # Use all available symbols
                '--fg-only',           # Use foreground colors only for better compatibility
                '--stretch',           # Stretch to fit dimensions
                str(image_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                print(result.stdout)
                return True
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def _render_img2txt(self, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using img2txt (libcaca)"""
        try:
            cmd = [
                'img2txt',
                '-W', str(max_width),
                '-H', str(max_height),
                str(image_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                print(result.stdout)
                return True
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def _render_jp2a(self, image_path: Path, max_width: int, max_height: int) -> bool:
        """Render image using jp2a (JPEG to ASCII)"""
        # Only works with JPEG files
        if not str(image_path).lower().endswith(('.jpg', '.jpeg')):
            return False
        
        try:
            cmd = [
                'jp2a',
                '--width', str(max_width),
                '--height', str(max_height),
                str(image_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                print(result.stdout)
                return True
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def get_capabilities_info(self) -> dict:
        """Get information about available rendering capabilities"""
        return {
            'terminal_type': self.terminal_type,
            'available_renderers': self.available_renderers,
            'preferred_renderer': self.available_renderers[0] if self.available_renderers else None,
            'supports_true_images': 'kitty' in self.available_renderers or 'iterm2' in self.available_renderers
        }
    
    def print_capabilities(self):
        """Print information about rendering capabilities"""
        info = self.get_capabilities_info()
        
        console.print(f"[bold blue]Terminal Image Rendering Capabilities:[/bold blue]")
        console.print(f"Terminal Type: [cyan]{info['terminal_type']}[/cyan]")
        console.print(f"Available Renderers: [green]{', '.join(info['available_renderers']) if info['available_renderers'] else 'None'}[/green]")
        console.print(f"Supports True Images: [{'green' if info['supports_true_images'] else 'red'}]{info['supports_true_images']}[/{'green' if info['supports_true_images'] else 'red'}]")
        
        if not info['available_renderers']:
            console.print("\n[yellow]💡 Tip: Install 'chafa' for ASCII art image rendering:[/yellow]")
            console.print("[dim]  • Ubuntu/Debian: sudo apt install chafa[/dim]")
            console.print("[dim]  • macOS: brew install chafa[/dim]")
            console.print("[dim]  • Fedora: sudo dnf install chafa[/dim]")