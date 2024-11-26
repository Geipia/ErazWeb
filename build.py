import os

def clean():
    """Remove temporary files."""
    os.system("find . -type f -name '*.pyc' -delete")
    os.system("find . -type d -name '__pycache__' -delete")

def install_dependencies():
    """Install dependencies."""
    os.system("pip install -r requirements.txt")

def build():
    """Build the project."""
    clean()
    install_dependencies()

if __name__ == "__main__":
    build()
