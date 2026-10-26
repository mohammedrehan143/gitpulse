from setuptools import find_namespace_packages, setup

setup(
    name="gitpulse-backend",
    version="0.1.0",
    packages=find_namespace_packages(
        where=".", include=["src*", "backend*", "tests*", "migrations*"]
    ),
    package_dir={"": "."},
    py_modules=["main"],
)
