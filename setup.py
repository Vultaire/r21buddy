from distutils.core import setup
import py2exe

version = "1.1"


setup(
    name="r21buddy",
    version=version,
    author="Paul Goins",
    author_email="general@vultaire.net",
    url="https://github.com/Vultaire/r21buddy",
    description="Utilities for preparing StepMania songs for use with ITG R21.",
    download_url="https://github.com/Vultaire/r21buddy/zipball/master",
    #platforms=["nt", "posix"],  # Not sure of format...
    license="MIT",
    packages=["r21buddy"],

    # py2exe-specific
    console=[
        "r21buddy/r21buddy.py",
        "r21buddy/oggpatch.py",
        ],
    windows=[
        "r21buddy/r21buddy_gui.py",
        "r21buddy/oggpatch_gui.py",
        ],
    zipfile=None,
    options={
        "py2exe": {
            # Currently, the GUIs will not build if the below options
            # are enabled.
            #"bundle_files": 1,
            },
        },
    )
