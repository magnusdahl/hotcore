from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="hotcore",
    version="0.1.0",
    author="Original Author",
    author_email="author@example.com",
    description="A Redis-based hierarchical entity model for application data management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/hotcore",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "redis",
    ],
    extras_require={
        "dev": [
            "pytest",
            "fakeredis",
            "black",
            "isort",
            "mypy",
            "flake8",
            "build",
            "twine",
        ],
    },
) 