"""兼容层：为未安装 PEP 517 构建后端的环境提供 setup.py。

Compatibility shim: provides ``setup.py`` for environments without a PEP 517
build backend installed (``python setup.py sdist`` still works there).

推荐方式仍然是 / The recommended path remains::

    python -m build
"""

from pathlib import Path

from setuptools import find_packages, setup

README = Path(__file__).with_name("README.md")

setup(
    name="agentcubicle",
    version="1.0.0",
    description=(
        "Zero-dependency isolated workspaces, pre-action authorization "
        "and tamper-evident audit for AI agents"
    ),
    long_description=README.read_text(encoding="utf-8") if README.exists() else "",
    long_description_content_type="text/markdown",
    author="gitstq",
    license="MIT",
    packages=find_packages(include=["agentcubicle", "agentcubicle.*"]),
    python_requires=">=3.8",
    install_requires=[],
    entry_points={"console_scripts": ["cubicle=agentcubicle.cli:main"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
    ],
)
