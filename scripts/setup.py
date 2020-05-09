from setuptools import setup, find_packages
print(find_packages())
setup(
    name = "Wheezy-extractor",
    version = "1.0",
    packages = find_packages(),
    entry_points = """
    [babel.extractors]
    wheezyhtml = extractor.wheezy_extractor:extract_wheezy
    """
)
