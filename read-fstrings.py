#! /usr/bin/env python3
import io, sys

eof = False
index = 0
maxtext = 5168
maxbyte = 0xf134
beof = False

sys.stdout = open('instructions-fstr.txt', 'w')

def readcstr(fi):
    global eof, index
    charlist = []
    while not eof:
        char = fi.read(1)
        if len(char) == 0:
            eof = True
        else:
            index += 1
            # if index >= maxbyte:
            if index >= maxtext:
                eof = True
            if char == b'\0':
                break
            charlist.append(char)
    return b''.join(charlist)

def readzeroblock(fi):
    global beof, index
    zerocount = 0
    while not beof:
        char = fi.read(1)
        if len(char) == 0:
            beof = True
        else:
            if index >= maxbyte:
                beof = True
            if char == b'\0':
                index += 1
                zerocount += 1
            else:
                fi.seek(-1, io.SEEK_CUR) # Unread a byte
                break
    return zerocount

def guaranteed_read(f, n):
    bys = f.read(n)
    assert len(bys) == n, 'need {}, got only {}'.format(n, len(bys))
    return bys

emptylinecnt = 0

# def printempty():
#     print('<{} empty lines>'.format(emptylinecnt))

with open('sprint.elf', 'rb') as spf:
    spf.seek(0x2020)
    while not eof:
        preindex = index
        s = readcstr(spf)
        # if s == b'':
        #     emptylinecnt += 1
        # else:
        #     if emptylinecnt > 0:
        #         printempty()
        #         emptylinecnt = 0
        #     try:
        #         print(s.decode())
        #     except UnicodeDecodeError:
        #         print(s)
        print('{:05d}:  {}'.format(preindex, s.decode()))
    preindex = index
    cz = readzeroblock(spf)
    print("{:05d}: #db b'\\0' * {}".format(preindex, cz))
    preindex = index
    print("{:05d}: #db {}".format(preindex, guaranteed_read(spf, maxbyte - index)))
    print("{:05d}: #end".format(maxbyte))

# if emptylinecnt > 0:
#     printempty()
