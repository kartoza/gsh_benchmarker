#!/usr/bin/env python3
"""
Test Configuration Management for GSH Benchmarker Suite

Provides persistence for test configuration settings like
last used concurrency levels, request counts, etc.
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class TestConfiguration:
    """Configuration for benchmark test parameters"""
    last_concurrency_list: List[int]
    last_total_requests: int
    last_updated: str
    
    def __post_init__(self):
        if isinstance(self.last_concurrency_list, str):
            # Handle case where it's loaded as a string from JSON
            self.last_concurrency_list = [int(x.strip()) for x in self.last_concurrency_list.split(',')]
        self.last_updated = datetime.now().isoformat()

class TestConfigManager:
    """Manager for test configuration persistence"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize config manager with optional custom config file path"""
        if config_file is None:
            # Store config in project root
            self.config_file = Path.cwd() / "test_config.json"
        else:
            self.config_file = Path(config_file)
        
        self.config = self._load_config()
    
    def _load_config(self) -> TestConfiguration:
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return TestConfiguration(**data)
            else:
                # Create default configuration
                return TestConfiguration(
                    last_concurrency_list=[1, 10, 100, 500, 1000],
                    last_total_requests=5000,
                    last_updated=datetime.now().isoformat()
                )
        except Exception:
            # Fallback to default on any error
            return TestConfiguration(
                last_concurrency_list=[1, 10, 100, 500, 1000],
                last_total_requests=5000,
                last_updated=datetime.now().isoformat()
            )
    
    def _save_config(self) -> bool:
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
            return True
        except Exception:
            return False
    
    def get_last_concurrency_list(self) -> List[int]:
        """Get the last used concurrency list"""
        return self.config.last_concurrency_list.copy()
    
    def get_last_total_requests(self) -> int:
        """Get the last used total requests"""
        return self.config.last_total_requests
    
    def set_concurrency_list(self, concurrency_list: List[int]) -> bool:
        """Set and save the concurrency list"""
        self.config.last_concurrency_list = concurrency_list.copy()
        self.config.last_updated = datetime.now().isoformat()
        return self._save_config()
    
    def set_total_requests(self, total_requests: int) -> bool:
        """Set and save the total requests"""
        self.config.last_total_requests = total_requests
        self.config.last_updated = datetime.now().isoformat()
        return self._save_config()
    
    def update_test_config(self, concurrency_list: List[int], total_requests: int) -> bool:
        """Update and save both concurrency list and total requests"""
        self.config.last_concurrency_list = concurrency_list.copy()
        self.config.last_total_requests = total_requests
        self.config.last_updated = datetime.now().isoformat()
        return self._save_config()

def parse_concurrency_list(concurrency_input: str) -> List[int]:
    """Parse comma-separated concurrency values into a list of integers"""
    try:
        # Split by comma, strip whitespace, convert to int
        concurrency_list = []
        for item in concurrency_input.split(','):
            value = int(item.strip())
            if value > 0:  # Only include positive values
                concurrency_list.append(value)
        
        # Remove duplicates and sort
        concurrency_list = sorted(list(set(concurrency_list)))
        return concurrency_list
    except (ValueError, AttributeError):
        return []

def validate_concurrency_list(concurrency_list: List[int], total_requests: int) -> List[int]:
    """Remove concurrency levels that are greater than total requests"""
    valid_concurrency = [c for c in concurrency_list if c <= total_requests]
    return sorted(valid_concurrency)

def format_concurrency_list(concurrency_list: List[int]) -> str:
    """Format concurrency list as comma-separated string"""
    return ', '.join(map(str, concurrency_list))