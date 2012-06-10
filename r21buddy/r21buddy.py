"""Script to generate a R21-compatible song directory.

This is the console version; a GUI version is intended eventually.

"""

from __future__ import absolute_import

import os, sys, argparse, shutil
from r21buddy import oggpatch
from r21buddy.logger import logger


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
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output.")
    return ap.parse_args()

def create_target_dir_structure(target_dir, verbose=False):
    song_dir = os.path.join(target_dir, "In The Groove 2", "Songs")
    if not os.path.exists(song_dir):
        os.makedirs(os.path.join(target_dir, "In The Groove 2", "Songs"))
        if verbose:
            logger.info("Created directory: {0}".format(song_dir))
    elif not os.path.isdir(song_dir):
        raise Exception("Target path is not a directory", song_dir)
    else:
        if verbose:
            logger.info("Directory already exists: {0}".format(song_dir))

def copy_songs(input_path, target_dir, verbose=False):
    all_files = [os.path.join(input_path, f) for f in os.listdir(input_path)]
    dirs = [f for f in all_files if os.path.isdir(f)]

    # If directories present: recurse into them.
    if len(dirs) > 0:
        for d in dirs:
            copy_songs(d, target_dir, verbose=verbose)

    # Check whether this is a song directory.
    files = [f for f in all_files if os.path.isfile(f)]
    stepfile_exists = any(
        (f.endswith(".sm") or f.endswith(".dwi"))
        for f in all_files)

    if not stepfile_exists:
        return

    # This is a song directory.  Are we compatible?
    # Currently we must have a .sm and .ogg file.  .dwi and .mp3 are
    # not supported.
    sm_exists = any(f.endswith(".sm") for f in all_files)
    ogg_exists = any(f.endswith(".ogg") for f in all_files)
    mp3_exists = any(f.endswith(".mp3") for f in all_files)

    if not sm_exists:
        logger.error("Directory {0}: Could not find .sm; only .dwi was found.  Skipping.".format(input_path))
        return
    if not ogg_exists:
        if any(f.endswith(".mp3") for f in all_files):
            logger.error("Directory {0}: Could not find .ogg; only .mp3 was found.  Skipping.".format(input_path))
        else:
            logger.error("Directory {0}: Could not find .ogg.  Skipping.".format(input_path))
        return

    # We are compatible.  Check for destination directory; complain
    # LOUDLY if not able to create it.
    song_dir_name = os.path.split(input_path)[-1]
    target_song_dir = os.path.join(
        target_dir, "In The Groove 2", "Songs", song_dir_name)
    if os.path.exists(target_song_dir):
        logger.error("ERROR: {0} already exists; not copying files from {1}.".format(target_song_dir, input_path))
        return

    os.makedirs(target_song_dir)
    for ext in ".sm", ".ogg":
        for src_file in (f for f in all_files if f.endswith(ext)):
            dest_file = os.path.join(
                target_song_dir, os.path.basename(src_file))
            if verbose:
                logger.info("Copying: {0}\n     to: {1}".format(src_file, dest_file))
            shutil.copyfile(src_file, dest_file)

def patch_length(target_dir, verbose=False):
    song_dir = os.path.join(target_dir, "In The Groove 2", "Songs")
    all_files = [os.path.join(song_dir, f) for f in os.listdir(song_dir)]
    dirs = [d for d in all_files if os.path.isdir(d)]
    for song_dir in dirs:
        song_files = (os.path.join(song_dir, f) for f in os.listdir(song_dir))
        ogg_files = (f for f in song_files if f.endswith(".ogg"))
        for ogg_file in ogg_files:
            if verbose:
                logger.info("Patching file: {0}".format(ogg_file))
            oggpatch.patch_file(ogg_file, verbose=verbose)

def run(target_dir, input_paths, length_patch=True, verbose=False, ext_logger=None):
    global logger
    if logger is not None:
        logger = ext_logger
        oggpatch.set_logger(logger)
    create_target_dir_structure(target_dir, verbose=verbose)

    for input_path in input_paths:
        copy_songs(input_path, target_dir, verbose=verbose)

    # *NOTE:* If no input paths are specified, this tool can be used
    # to patch the length on existing ogg files in the target dir.
    if length_patch:
        patch_length(target_dir, verbose=verbose)

def main():
    options = parse_args()
    run(options.target_dir, options.input_path,
        length_patch=options.length_patch, verbose=options.verbose)
    return 0

if __name__ == "__main__":
    sys.exit(main())
