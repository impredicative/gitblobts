from pathlib import Path
from typing import List

from setuptools import setup, find_packages


def parse_requirements(filename: str) -> List[str]:
    """Return requirements from requirements file.

    The "MANIFEST.in" file must exist with the line "include requirements.in".
    """
    # Ref: https://stackoverflow.com/a/50368460/
    requirements = (Path(__file__).parent / filename).read_text().strip().split('\n')
    requirements = [r.strip() for r in requirements]
    requirements = [r for r in sorted(requirements) if r and not r.startswith('#')]
    return requirements


setup(
    name='gitblobts',
    version='0.0.2',
    description='git-backed time-indexed blob storage',
    keywords='git bytes mirroring storage time',
    long_description=Path(__file__).with_name('README.md').read_text().strip(),
    long_description_content_type='text/markdown',
    url='https://github.com/impredicative/gitblobts/',
    packages=find_packages(exclude=['tests', 'util']),
    install_requires=parse_requirements('requirements.in'),
    python_requires='>=3.7',
    package_data={
        'gitblobts': ['logging.conf'],
    },
    classifiers=[  # https://pypi.org/classifiers/
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Topic :: Communications :: File Sharing",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: System :: Archiving",
        "Topic :: System :: Archiving :: Mirroring",
    ],
)

"""
Build steps:
rm -rf ./build/* ./dist/*
python ./setup.py sdist bdist_wheel
twine upload ./dist/*
"""
