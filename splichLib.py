# Splich.py
# Splits files into parts, or in chunk_size
# Splich is a file splitting tool that allows you to split a file into parts, and reassembles them

# https://github.com/shine-jayakumar/splich

# Author: Shine Jayakumar
# https://github.com/shine-jayakumar
#
# MIT License

# Copyright (c) 2022 Shine Jayakumar

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import glob
import argparse
import hashlib
from datetime import datetime
from configparser import ConfigParser
import sys

VERSION = 'v.1.4'

VERBOSE = False


def fileSplit(file, parts=None, chunk_size=None):
    '''
    Splits files into parts, or in chunk_size
    '''
    if not file:
        return False
    if not parts and not chunk_size:
        return False
        
    fsize = os.path.getsize(file)
    
    if chunk_size and chunk_size > fsize:
        raise ValueError('Chunk size cannot be greater than file size')

    #vvprint(f'Source file: {file}')
    #vvprint(f'Size: {fsize}')

    segment_size = 0

    if parts:
        segment_size = fsize // parts
    else:
        segment_size = chunk_size
    
    if segment_size < 1:
        raise ValueError('At least 1 byte required per part')

    #vvprint(f'Segment Size: {segment_size}')

    fdir, fname = os.path.split(file)
    # fname = fname.split('.')[0]
    fname = os.path.splitext(fname)[0]
    
    #vvprint('Generating hash')
    hash = _gethash(file)
    start_time = datetime.today().strftime("%m%d%Y_%H%M")

    #vvprint(f'Hash: {hash}\n\n')
    #vvprint(f'Reading file: {file}')

    with open(file,'rb') as fh:
        fpart = 1
        while fh.tell() != fsize:
            if parts:
                # check if this is the last part
                if fpart == parts:
                    # size of the file - wherever the file pointer is
                    # the last part would contain segment_size + whatever is left of the file
                    segment_size = fsize - fh.tell()

            chunk = fh.read(segment_size)
            part_filename = os.path.join(fdir, f'{fname}_{start_time}_{fpart}.prt')
            #vvprint(f'{part_filename} Segment size: {segment_size} bytes')
            with open(part_filename, 'wb') as chunk_fh:
                chunk_fh.write(chunk)
            fpart += 1

        # hashfile generation
        hashfilename = f'{fname}_hash_{start_time}'
        hashfile_path = os.path.join(fdir, hashfilename)
        #vvprint(f'Hashfile: {hashfile_path}')
        with open(hashfile_path, 'w') as hashfile:
            hashfile.write(hash)
        
        # auto-stitch config file generation
        #vvprint('Generating auto-stitch config file')
        if _generate_stitch_config(filename=file, hashfile=hashfilename):
            pass
            #vvprint('Saved stitch.ini')
        else:
            pass
            #vvprint('Could not create auto-stitch config. Stitch files manually.')

        return True   


def fileStitch(file, outfile=None, hashfile=None):
    '''
    Stitches the parts together
    '''
    # d:\\somedir\\somefile.txt to 
    # d:\\somedir and somefile.txt

    if not file:
        return False

    fdir, fname = os.path.split(file)
    # fname = fname.split('.')[0]
    fname = os.path.splitext(fname)[0]
    
    file_parts = glob.glob(os.path.join(fdir,  f'{fname}_*.prt'))
    file_parts = _sort_file_parts(file_parts)
    
    if not file_parts:
        raise FileNotFoundError('Split files not found')

    if outfile:
        # if just the filename
        if os.path.split(outfile)[0] == '':
            # create the file in input dir (fdir)
            outfile = os.path.join(fdir, outfile)

            
    with open(outfile or file, 'wb') as fh:
        for filename in file_parts:
            buffer = b''
            with open(filename, 'rb') as prt_fh:
                buffer = prt_fh.read()
                fh.write(buffer)

    
    if hashfile:
        if _checkhash(outfile or file, hashfile):
            return True
        else:
            return False


def _gethash(file):
    '''
    Returns the hash of file
    '''
    hash = None
    with open(file, 'rb') as fh:
        hash = hashlib.sha256(fh.read()).hexdigest()
    return hash


def _checkhash(file, hashfile):
    '''
    Compares hash of a file with original hash read from a file
    '''
    curhash = None
    orghash = None
    curhash = _gethash(file)
    with open(hashfile, 'r') as fh:
        orghash = fh.read()

    return curhash == orghash

def _getpartno(filepart):
    '''
    Returns the part number from a part filename
    Ex: flask_05112022_1048_3.prt -> 3
    '''
    return int(filepart.split('_')[-1].split('.')[0])


def _sort_file_parts(file_part_list):
    '''
    Returns a sorted list of part filenames based on the part number
    Ex: ['flask_05112022_1048_3.prt', 'flask_05112022_1048_1.prt', 'flask_05112022_1048_2.prt'] ->
        ['flask_05112022_1048_1.prt', 'flask_05112022_1048_2.prt', 'flask_05112022_1048_3.prt']
    '''
    # creates list of (prt_no, part)
    fparts = [(_getpartno(prt), prt) for prt in file_part_list]
    fparts.sort(key=lambda x: x[0])
    fparts = [prt[1] for prt in fparts]
    return fparts
        

def _generate_stitch_config(filename, hashfile):
    '''
    Generates auto-stitch config file
    '''
    try:
        with open('stitch.ini', 'w') as configfile:
            config = ConfigParser()
            config.add_section('stitch')
            config.set('stitch', 'filename', filename)
            config.set('stitch', 'hashfile', hashfile)

            config.add_section('settings')
            config.set('settings', 'verbose', 'True')
            config.write(configfile)
    except Exception as ex:
        #print(f'Error while creating auto-stitch config file: {str(ex)}')
        stitch_config_path = os.path.join(os.getcwd(), 'stitch.ini')
        if os.path.exists(stitch_config_path):
            os.remove(stitch_config_path)
        return False
    return True
