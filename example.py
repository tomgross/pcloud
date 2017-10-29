#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import glob
from pcloud import PyCloud


def read_in_chunks(infile, chunk_size=1024 * 8):
    while True:
        chunk = infile.read(chunk_size)
        if chunk:
            yield chunk
        else:
            return


class Backup:
    BLOCKED = ['', '.INI', '.MSI', '.EXE', '.STW', '.STC', '.DIF', '.SLK', '.SXD', '.STD', '.UOP', '.OTG', '.MML', '.JAR',
            '.PS1', '.TAP', '.HTML', '.DIP', '.DCH', '.SCH', '.CLASS', '.MP3', '.WAV', '.SWF', '.WMV', '.VOB', '.ASF',
            '.MP4', '.MKV', '.FLV', '.WMA', '.MID', '.M3U', '.M4U', '.DJVU', '.SVG', '.NEF', '.TIFF', '.TIF', '.RAW',
            '.GIF', '.BMP', '.VCD', '.ISO', '.TBK', '.BZ2', '.PAQ', '.ARC', '.VMX', '.VMDK', '.VDI', '.SLDM', '.SLDX',
            '.STI', '.SXI', '.HWP', '.EDB', '.POTM', '.POTX', '.PPAM', '.PPSM', '.POT', '.PPTM', '.XLTM', '.XLTX',
            '.XLC', '.XLM', '.XLT', '.XLW', '.DOTX', '.DOTM', '.DOT', '.DOCM', '.DOCB', '.ONETOC2', '.WK1', '.WKS']

    def __init__(self, username, password):
        self.pc = PyCloud(username, password)

    def blocked_ext(self, f):
        """
        Check the BLOCKED list if the file extension is locked for backup
        """
        return os.path.splitext(f)[1] in self.BLOCKED

    def create_folder(self, name, parent_id=0):
        """
        Create a new folder based on [parent_id]. Returns the [folderid] of the new folder
        """
        res = self.pc.createfolder(folderid=parent_id, name=name)
        res = res.get('metadata')
        if res:
            return res.get('folderid')
        return None

    def exist_folder(self, name, parent_id=0):
        """
        Checks if the folder name exists in the parent folder based on [parent_id].
        Returns the [folderid] if exists
        """
        res = self.pc.listfolder(folderid=parent_id)
        res = res.get('metadata').get('contents')
        for aux in res:
            if aux.get('parentfolderid') == parent_id and aux.get('name') == name:
                return aux.get('folderid')
        return 0

    def upload(self, path, computer_name, folder_id=0):
        """
        Receives the path of the backup folder and re-creates the folder tree
        Receives computer_name to know the source of the backup.
        Upload all files and subfolders
        """
        try:
            folder_names = []
            if computer_name:
                # Decode string for remove incompatible characters
                new_path = computer_name + os.sep + path.replace(':', '-drive').decode('cp1252')
                
                # convert the folder tree to the list of names from root to node
                folder_names.extend(new_path.split('\\'))
            else:
                folder_names.append(os.path.basename(path))

            # Create the folder tree in pcloud
            for name in folder_names:
                exist = self.exist_folder(name, folder_id)
                if exist:
                    folder_id = exist
                else:
                    folder_id = self.create_folder(name, folder_id)

            path = path + os.sep
            # only files
            for f in sorted(glob.glob(path + '*.*'), key=os.path.getsize):
                self.upload_file(f, folder_id)

            # only folders
            # Recursively call the upload for each subfolder
            for f in sorted(glob.glob(path + '**/'), key=os.path.getsize):
                self.upload(f[:-1], None, folder_id)

            return 1
        except:
            return 0

    def upload_file(self, file_path, folder_id):
        """
        Upload all files to folder based on folder_id
        """
        try:
            filename = os.path.basename(file_path).upper()
            file_up = self.pc.file_open(flags=0x0040, name=filename, folderid=folder_id)
            
            # Verify that the file exists or file extension is blocked
            if self.pc.file_read(fd=file_up.get('fd'), count=4) or self.blocked_ext(filename):
                return
            
            # Upload the bytes of file
            with open(file_path, 'rb') as f:
                for chunk in read_in_chunks(f):
                    self.pc.file_write(fd=file_up.get('fd'), data=chunk)
            self.pc.file_close(fd=file_up.get('fd'))
        except:
            return


# How to use this:
Backup("user", "pass").upload("C:\\Users\\Admin\\PycharmProjects\\Cloud\\folder_to_backup", "computer1")
