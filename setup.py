from setuptools import find_namespace_packages, setup

setup(
    name="gitpulse",
    version="0.1.0",
    packages=find_namespace_packages(where=".", include=["backend*", "agent_runtime*"]),
    package_dir={"": "."},
)
