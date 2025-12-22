#!/usr/bin/env python3
"""
Test runner for download functionality tests
"""
import sys
import os
import subprocess

def run_tests():
    """Run the test suite"""
    # Add the project root to Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, project_root)
    
    # Change to the project root directory
    os.chdir(project_root)
    
    # Run pytest with the test files
    test_files = [
        os.path.join(os.path.dirname(__file__), 'test_api_controller.py'),
        os.path.join(os.path.dirname(__file__), 'test_app_controller.py')
    ]
    
    # Check if required dependencies are available
    missing_deps = []
    
    # Use the virtual environment's python if available for dependency checks
    venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
    if os.path.exists(venv_python):
        python_cmd = venv_python
    else:
        python_cmd = 'python'
    
    # Check dependencies using the appropriate python
    try:
        result = subprocess.run([python_cmd, '-c', 'import pytest'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            missing_deps.append("pytest")
    except:
        missing_deps.append("pytest")
    
    try:
        result = subprocess.run([python_cmd, '-c', 'import pytest_mock'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            missing_deps.append("pytest-mock")
    except:
        missing_deps.append("pytest-mock")
    
    try:
        result = subprocess.run([python_cmd, '-c', 'from Crypto.Cipher import AES'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            missing_deps.append("pycryptodome")
    except:
        missing_deps.append("pycryptodome")
    
    if missing_deps:
        print("\n❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n📦 Install missing dependencies with:")
        print("   python3 -m venv download/tests/venv")
        print("   source download/tests/venv/bin/activate")
        print("   pip install -r download/tests/requirements-minimal.txt")
        return 1
    
    # Use the virtual environment's python if available
    venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
    if os.path.exists(venv_python):
        python_cmd = venv_python
    else:
        python_cmd = 'python'
    
    cmd = [
        python_cmd, '-m', 'pytest', 
        *test_files,
        '-v',
        '--tb=short',
        '--disable-warnings'
    ]
    
    print(f"Running tests from: {project_root}")
    print(f"Test files: {', '.join(test_files)}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("\n❌ pytest not found. Please install test dependencies:")
        print("pip install -r download/tests/requirements-minimal.txt")
        return 1

if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
