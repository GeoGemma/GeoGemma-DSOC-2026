#!/usr/bin/env python3
"""
Setup script for the GIS AI Agent.

This script provides a way to install the GIS AI Agent as a package,
making it easier to use and distribute.
"""

from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="gis_agent",
    version="0.1.0",
    description="A powerful GIS and sustainability analysis tool using MCP Server with Gemini 2.5 Pro",
    author="GIS AI Agent Team",
    author_email="Khalilzaryani007@gmail.com",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "gis-agent=src.main:main",
        ],
    },
) 