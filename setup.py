from distutils.core import setup
import py2exe

version = "0.1"

setup(
    name="r21buddy",
    version=version,
    author="Paul Goins",
    author_email="general@vultaire.net",
    url="https://github.com/Vultaire/r21buddy",
    description="Utilities for preparing StepMania songs for use with ITG R21.",
    download_url="https://github.com/Vultaire/r21buddy/zipball/master",
    #platforms=["nt", "posix"],  # Not sure of format...
    license="BSD",
    packages=["r21buddy"],
    # py2exe-specific
    console=[
        "r21buddy/r21buddy.py",
        "r21buddy/oggpatch.py",
        ],
    zipfile=None,
    options={
        "py2exe": {
            "bundle_files": 1,
            },
        },
    )
