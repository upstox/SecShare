import subprocess
import sys

def run_app(app_path):
    """Function to run a Python app."""
    subprocess.Popen([sys.executable, app_path])

if __name__ == "__main__":
    # Start the upload app
    run_app('/opt/company/secshare-file-sharing-tool/upload/run.py')

    # Start the download app
    run_app('/opt/company/secshare-file-sharing-tool/download/run.py')

    # Wait for both processes to finish
    while True:
        pass  # Keep the process running
