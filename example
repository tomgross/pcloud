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
    EXTS = ['', '.INI', '.MSI', '.EXE', '.STW', '.STC', '.DIF', '.SLK', '.SXD', '.STD', '.UOP', '.OTG', '.MML', '.JAR',
            '.PS1', '.TAP', '.HTML', '.DIP', '.DCH', '.SCH', '.CLASS', '.MP3', '.WAV', '.SWF', '.WMV', '.VOB', '.ASF',
            '.MP4', '.MKV', '.FLV', '.WMA', '.MID', '.M3U', '.M4U', '.DJVU', '.SVG', '.NEF', '.TIFF', '.TIF', '.RAW',
            '.GIF', '.BMP', '.VCD', '.ISO', '.TBK', '.BZ2', '.PAQ', '.ARC', '.VMX', '.VMDK', '.VDI', '.SLDM', '.SLDX',
            '.STI', '.SXI', '.HWP', '.EDB', '.POTM', '.POTX', '.PPAM', '.PPSM', '.POT', '.PPTM', '.XLTM', '.XLTX',
            '.XLC', '.XLM', '.XLT', '.XLW', '.DOTX', '.DOTM', '.DOT', '.DOCM', '.DOCB', '.ONETOC2', '.WK1', '.WKS']

    def __init__(self):
        self.pc = PyCloud(b'johnalb2@pokemail.net', b'123qwe..')

    def blocked_ext(self, f):
        return os.path.splitext(f)[1] in self.EXTS

    def create_folder(self, name, sub_id=0):
        res = self.pc.createfolder(folderid=sub_id, name=name)
        res = res.get('metadata')
        if res:
            return res.get('folderid')
        return None

    def exist_folder(self, name, folder_id=0):
        res = self.pc.listfolder(folderid=folder_id)
        res = res.get('metadata').get('contents')
        for aux in res:
            if aux.get('parentfolderid') == folder_id and aux.get('name') == name:
                return aux.get('folderid')
        return 0

    def upload(self, src, computer_name, folder_id=0):
        try:
            folder_names = []
            if computer_name:
                new_src = computer_name + os.sep + src.replace(':', '-drive').decode('cp1252')
                folder_names.extend(new_src.split('\\'))
            else:
                folder_names.append(os.path.basename(src))

            for name in folder_names:
                exist = self.exist_folder(name, folder_id)
                if exist:
                    folder_id = exist
                else:
                    folder_id = self.create_folder(name, folder_id)

            src = src + os.sep
            # only files
            for f in sorted(glob.glob(src + '*.*'), key=os.path.getsize):
                self.upload_file(f, folder_id)

            # only folders
            for f in sorted(glob.glob(src + '**/'), key=os.path.getsize):
                self.upload(f[:-1], None, folder_id)

            return 1
        except:
            return 0

    def upload_file(self, file_path, folder):
        try:
            filename = os.path.basename(file_path).upper()
            file_up = self.pc.file_open(flags=0x0040, name=filename, folderid=folder)
            if self.pc.file_read(fd=file_up.get('fd'), count=4) or self.blocked_ext(filename):
                return

            with open(file_path, 'rb') as f:
                for chunk in read_in_chunks(f):
                    self.pc.file_write(fd=file_up.get('fd'), data=chunk)
            self.pc.file_close(fd=file_up.get('fd'))
        except:
            return


# How to use this:
Backup().upload("C:\\Users\\Admin\\PycharmProjects\\Cloud\\folder_to_backup", "computer1")
