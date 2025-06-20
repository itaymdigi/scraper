#!/usr/bin/env python3
"""
Test runner script for the web scraper project.
"""

import sys
import subprocess
import os


def run_tests(test_type="all", verbose=True):
    """
    Run tests for the web scraper project
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'all')
        verbose: Whether to run in verbose mode
    """
    # Ensure we're in the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add test paths based on type
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    # Run the tests
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for the web scraper")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"], 
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="Run in quiet mode"
    )
    
    args = parser.parse_args()
    
    exit_code = run_tests(
        test_type=args.type,
        verbose=not args.quiet
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 