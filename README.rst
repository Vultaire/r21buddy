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

oggpatch.py is a single-file patcher, likely very similar to existing
patchers out there.  It should be capable of length-patching any ogg
files; at least, I have not yet found a valid Ogg file it won't patch.
It can either do in-place patching or create a patched copy.

::

  # Display help for oggpatch script
  python -m r21buddy.oggpatch -h

r21buddy.py is basically a wrapper around oggpatch.py which provides
the ability to recursively patch a directory of files.  Again; files
are not patched in place.  It will output its files in an
ITG2-compatible directory structure to the location of your choice.
(If you really want, you could output straight to a USB thumb drive,
although the performance might be less than stellar.)

::

  # Display help for r21buddy script
  python -m r21buddy.r21buddy -h
  
  # Patch all songs on an R21-prepared thumbdrive.
  python -m r21buddy.r21buddy <path_to_thumb_drive (e:\, etc.)>
  
  # Patch and copy songs from a source directory to a thumb drive
  python -m r21buddy.r21buddy -i <source_dir> <path_to_thumb_drive>

Finally, there are GUI versions::

  # Run GUI version of oggpatch
  python -m r21buddy.oggpatch_gui
  
  # Run GUI version of r21buddy
  python -m r21buddy.r21buddy_gui

Requirements:

- Python 2.7, or Python 2.6 with the argparse library.

- GUI is driven by Tkinter, so Tk *may* be required if it isn't
  auto-installed by your distro.

Windows
-------

Binaries are available at http://vultaire.net/files/r21buddy/bin/.

Alternatively, get Python 2.7 and you can run this directly in the
same way as for Linux users.

Finally, you can build your own copy via py2exe via::

  python setup.py py2exe

**Known issue:** The GUIs seem to have issues with non-ASCII
characters in path names.  This only seems to affect the Windows
version, and at the time of discovery appeared to be a Tkinter-related
bug, although I am not 100% sure.  If you encounter crashes or errors,
try using the console versions.
