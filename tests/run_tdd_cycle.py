#!/usr/bin/env python3
"""
TDD Cycle Runner - Educational Script
=====================================

This script guides you through the TDD cycle step by step.
It shows you exactly what's happening at each phase.
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_phase(phase: str, color: str):
    """Print a phase header"""
    print(f"\n{color}{BOLD}{'=' * 60}")
    print(f"{phase}")
    print(f"{'=' * 60}{RESET}\n")

def run_tests(test_file: str) -> bool:
    """Run pytest and return True if tests pass"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent  # Run from data-ingestion directory
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    """Guide through the TDD cycle"""
    
    print(f"{BOLD}Welcome to the TDD Implementation Guide!{RESET}")
    print("\nWe'll implement multi-platform support using Test-Driven Development.")
    print("Remember: TDD = Red → Green → Refactor\n")
    
    # Phase 1: RED
    print_phase("PHASE 1: RED - Write Failing Tests", RED)
    print("Purpose: Define the expected behavior through tests BEFORE implementation")
    print("Expected: All tests should FAIL because we haven't written any code yet\n")
    
    input(f"{YELLOW}Press Enter to run the tests (they will fail)...{RESET}")
    
    test_passed = run_tests("tests/unit/test_platform_base.py")
    
    if test_passed:
        print(f"\n{YELLOW}⚠️  Tests passed but they should have failed!")
        print("This means the implementation already exists.{RESET}")
    else:
        print(f"\n{GREEN}✓ Good! Tests failed as expected.{RESET}")
        print("This is the RED phase - we have failing tests that define our requirements.\n")
    
    # Explain what's next
    print(f"{BOLD}\nWhat the tests tell us:{RESET}")
    print("1. We need an APIProvider enum with BRIGHTDATA and APIFY values")
    print("2. We need a PlatformConfig dataclass with specific fields")
    print("3. We need a BasePlatformHandler abstract class")
    print("4. The base handler must define 6 abstract methods")
    print("5. The base handler cannot be instantiated directly")
    
    print(f"\n{BOLD}Next Step:{RESET}")
    print("Now we'll create the MINIMAL implementation to make these tests pass.")
    print("This is the GREEN phase - we write just enough code to pass the tests.\n")
    
    input(f"{YELLOW}Press Enter to see the implementation plan...{RESET}")
    
    # Phase 2: GREEN
    print_phase("PHASE 2: GREEN - Make Tests Pass", GREEN)
    print("We'll now create the minimal implementation:")
    print("1. Create platforms/__init__.py")
    print("2. Create platforms/base.py with our classes")
    print("3. Run tests again - they should pass!")
    
    print(f"\n{BOLD}The implementation will include:{RESET}")
    print("""
# platforms/base.py
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

class APIProvider(Enum):
    BRIGHTDATA = "brightdata"
    APIFY = "apify"

@dataclass
class PlatformConfig:
    name: str
    api_provider: APIProvider
    dataset_id: str
    date_format: str
    required_params: List[str]
    optional_params: List[str]
    api_endpoint: str
    media_fields: List[str]

class BasePlatformHandler(ABC):
    def __init__(self, config: PlatformConfig):
        self.config = config
    
    @abstractmethod
    def prepare_request_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    # ... other abstract methods
""")
    
    print(f"\n{BOLD}After implementation, tests should pass!{RESET}")
    
    # Phase 3: REFACTOR
    print_phase("PHASE 3: REFACTOR - Improve Code Quality", BLUE)
    print("Once tests pass, we can refactor to improve code quality:")
    print("- Add docstrings")
    print("- Add type hints")
    print("- Extract common patterns")
    print("- Improve naming")
    print("\nThe key: Tests must STAY GREEN during refactoring!")
    
    print(f"\n{BOLD}TDD Benefits Demonstrated:{RESET}")
    print("✓ We thought about the interface before implementation")
    print("✓ We have tests that document expected behavior")
    print("✓ We can refactor safely - tests will catch breaks")
    print("✓ We wrote minimal code - no over-engineering")
    
    print(f"\n{BOLD}Ready to continue with the implementation?{RESET}")
    print("\nNext steps:")
    print("1. Create the platforms/base.py file with minimal implementation")
    print("2. Run tests again - make them pass (GREEN)")
    print("3. Refactor the code while keeping tests green")
    print("4. Move to the next component (Facebook handler)")

if __name__ == "__main__":
    main()