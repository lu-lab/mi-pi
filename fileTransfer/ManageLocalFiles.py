import os
from os.path import join, split, isdir
from kivy.logger import Logger
from subprocess import check_output, CalledProcessError



def get_local_filepaths(local_savepath, remote_savepath):
    files_from = []
    files_to = []
    for root, dirs, files in os.walk(local_savepath):
        for f in files:
            if os.path.isfile(os.path.join(local_savepath, f)):
                files_from.append(join(root, f))
                files_to.append('/'.join([remote_savepath, f]))  # type: str

    return files_from, files_to


def cleanup_files(local_savepath, remote_savepath, rclone_name):
    files_from, files_to = get_local_filepaths(local_savepath, remote_savepath)
    Logger.debug('Upload: Source filepaths %s' % files_from)
    Logger.debug('Upload: Destination filepaths %s' % files_to)
    # this will return a list of paths on the remote (not recursive)
    remote_savepath = ':'.join([rclone_name, remote_savepath])
    try:
        res = check_output(["rclone", "lsf", remote_savepath])
        res = res.decode("utf-8")
        for src, dest in zip(files_from, files_to):
            (p, f) = split(dest)
            if not isdir(dest):
                if f in res:
                    # delete the local file to save disk space
                    os.remove(src)
                    Logger.debug('Deleting: file %s exists on remote' % src)
    except CalledProcessError:
        Logger.info('Upload Error: unable to upload to dropbox')
