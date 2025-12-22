#!/usr/bin/env python3
"""
Test runner for upload application tests
"""
import sys
import os
import subprocess
import platform

def main():
    """Run the test suite for upload application"""
    print("Running tests from:", os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../..'))
    
    # Add project root to Python path
    sys.path.insert(0, project_root)
    
    # Test files to run
    test_files = [
        os.path.join(script_dir, 'test_admin_controller.py'),
        os.path.join(script_dir, 'test_api_controller.py')
    ]
    
    print("Test files:", ', '.join(test_files))
    
    # Check if virtual environment exists
    venv_path = os.path.join(script_dir, 'venv')
    if os.path.exists(venv_path):
        if platform.system() == "Windows":
            python_cmd = os.path.join(venv_path, 'Scripts', 'python.exe')
        else:
            python_cmd = os.path.join(venv_path, 'bin', 'python')
    else:
        python_cmd = 'python3'
    
    # Check if pytest is available
    try:
        result = subprocess.run([python_cmd, '-m', 'pytest', '--version'], 
                              capture_output=True, text=True, cwd=script_dir)
        if result.returncode != 0:
            print("❌ pytest not available. Installing dependencies...")
            install_dependencies(python_cmd, script_dir)
    except FileNotFoundError:
        print("❌ Python not found. Please ensure Python is installed.")
        return 1
    
    # Run the tests
    cmd = [python_cmd, '-m', 'pytest'] + test_files + ['-v', '--tb=short', '--disable-warnings']
    print("Command:", ' '.join(cmd))
    print("-" * 50)
    
    result = subprocess.run(cmd, cwd=script_dir)
    
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed with exit code:", result.returncode)
    
    return result.returncode

def install_dependencies(python_cmd, script_dir):
    """Install test dependencies"""
    requirements_file = os.path.join(script_dir, 'requirements.txt')
    
    if os.path.exists(requirements_file):
        print("Installing dependencies from requirements.txt...")
        try:
            subprocess.run([python_cmd, '-m', 'pip', 'install', '-r', requirements_file], 
                          check=True, cwd=script_dir)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    else:
        print("❌ requirements.txt not found")
        return False
    
    return True

if __name__ == '__main__':
    sys.exit(main())
