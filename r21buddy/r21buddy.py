"""Script to generate a R21-compatible song directory.

This is the console version; a GUI version is intended eventually.

"""

import os, sys, argparse

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "target_dir",
        help=("Output directory.  NOTE: An ITG2-compatible directory "
              "structure will be created *within* this directory."))
    ap.add_argument(
        "-i", "--input-path", default=[], nargs="*",
        help=("Input path(s) to extract songs from."))
    ap.add_argument(
        "-n", "--no-length-patch", dest="length_patch",
        action="store_false", default=True,
        help="Skip patching of .ogg files.")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args()

def create_target_dir_structure(target_dir, verbose=False):
    song_dir = os.path.join(target_dir, "In The Groove 2", "Songs")
    if not os.path.exists(song_dir):
        os.makedirs(os.path.join(target_dir, "In The Groove 2", "Songs"))
        if verbose:
            print "Created directory:", song_dir
    elif not os.path.isdir(song_dir):
        raise Exception("Target path is not a directory", song_dir)
    else:
        if verbose:
            print "Directory already exists:", song_dir

def copy_songs(input_path, target_dir, verbose=False):
    pass

def patch_length(target_dir, verbose=False):
    song_dir = os.path.join(target_dir, "In The Groove 2", "Songs")
    all_files = (os.path.join(song_dir, f) for f in os.listdir(song_dir))
    dirs = (d for d in all_files if os.path.isdir(d))
    for song_dir in dirs:
        song_files = (os.path.join(os.listdir(song_dir), f)
                      for f in os.listdir(song_dir))
        ogg_files = (f for f in song_files if f.endswith(".ogg"))
        for ogg_file in ogg_files:
            oggpatch.patch_file(ogg_file, verbose=verbose)

def main():
    options = parse_args()

    create_target_dir_structure(options.target_dir, verbose=options.verbose)

    for input_path in options.input_path:
        copy_songs(input_path, options.target_dir, verbose=True)

    # *NOTE:* If no input paths are specified, this tool can be used
    # to patch the length on existing ogg files in the target dir.
    if options.length_patch:
        patch_length(options.target_dir, verbose=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
