==========
 r21buddy
==========

A pure Python version of the Ogg length hack for In The Groove 2 R21.

Currently this is a command line only program.  See --help for
details.  Drag-and-drop might work on Windows, but I am not certain.

Usage
=====

Linux
-----

Just run the scripts as-is.

oggpatch.py is complete::

  # Display help for oggpatch script
  python -m r21buddy.oggpatch -h

r21buddy.py is still under development::

  # Display help for r21buddy script
  python -m r21buddy.r21 -h
  
  # Patch all songs on an R21-prepared thumbdrive.
  python -m r21buddy.r21 <path_to_thumb_drive (e:\, etc.)>

Requirements: Python 2.7, or Python 2.6 with the argparse library.

Windows
-------

Get Python 2.7 and you can run this directly in the same way as for
Linux users.

Alternatively, compile a .exe using py2exe, pyinstaller or another
similar tool.  (I plan to eventually offer .exes myself; just haven't
got to it yet.)
