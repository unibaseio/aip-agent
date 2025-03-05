#!/usr/bin/env python3
import tomli
import re
from pathlib import Path

def read_pyproject_toml():
    """Read dependencies from pyproject.toml"""
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    return {
        "dependencies": pyproject["project"]["dependencies"],
        "python_requires": pyproject["project"]["requires-python"]
    }

def update_setup_py(dependencies, python_requires):
    """Update dependencies in setup.py"""
    setup_path = Path("setup.py")
    content = setup_path.read_text()
    
    # Update install_requires
    deps_str = "[\n        " + ",\n        ".join(f'"{dep}"' for dep in dependencies) + "\n    ]"
    content = re.sub(
        r"install_requires=\[[\s\S]*?\]",
        f"install_requires={deps_str}",
        content
    )
    
    # Update python_requires
    content = re.sub(
        r'python_requires="[^"]*"',
        f'python_requires="{python_requires}"',
        content
    )
    
    setup_path.write_text(content)

def main():
    try:
        print("Starting dependency synchronization...")
        config = read_pyproject_toml()
        update_setup_py(config["dependencies"], config["python_requires"])
        print("✅ Dependencies synchronized successfully!")
    except Exception as e:
        print(f"❌ Synchronization failed: {str(e)}")

if __name__ == "__main__":
    main() 