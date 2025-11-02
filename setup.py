"""
PRO-Ka-Po_Kaizen_Freak Application - Setup Configuration
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="PRO-Ka-Po_Kaizen_Freak",
    version="0.1.0",
    author="PRO-Ka-Po Team",
    author_email="contact@example.com",
    description="Komercyjna aplikacja do organizacji zadań - Kaizen Freak",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/PRO-Ka-Po_Kaizen_Freak",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Scheduling",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Natural Language :: Polish",
        "Natural Language :: English",
        "Natural Language :: German",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "kaizen-freak=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["resources/**/*"],
    },
)
