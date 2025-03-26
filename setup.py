from setuptools import setup, find_packages

setup(
    name="aip_agent", 
    version="0.1.4",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    author="felix",
    author_email="felix@unibase.io",
    description="AIP Agent for Unibase, include agent interraction, chain operation, agent tool management, etc.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/unibaseio/aip_agent",
    
    install_requires=[
        "mcp>=1.2.1",
        "chromadb>=0.6.0",
        "twikit>=2.3.3",
        "fastapi>=0.115.6",
        "instructor>=1.7.0",
        "opentelemetry-distro>=0.50b0",
        "opentelemetry-exporter-otlp-proto-http>=1.29.0",
        "pydantic-settings>=2.7.0",
        "pydantic>=2.10.4",
        "pyyaml>=6.0.2",
        "rich>=13.9.4",
        "typer>=0.15.1",
        "numpy>=2.2.1",
        "scikit-learn>=1.6.0",
        "loguru>=0.7.3",
        "autogen-core==0.4.8",
        "grpcio==1.70.0",
        "flask>=3.1.0",
        "gradio>=5.20.1",
        "membase>=0.1.8"
    ],

    python_requires=">=3.10",
) 