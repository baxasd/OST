from setuptools import setup, find_packages

setup(
    name="ost-capture",
    version="0.1",
    packages=find_packages(include=["src", "src.*"]),
    install_requires=[
        "opencv-python",
        "mediapipe",
        "numpy",
        "pyrealsense2",
        "filterpy"
    ],
    entry_points={
        "console_scripts": [
            "ost-capture=src.cli_entry:main"
        ]
    },
)
