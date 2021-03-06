#! /usr/bin/env python3

import sys

# Extracted from ushort[256] @ (mem + 0x7000)
# Prime indices are 0x0 while composite indices are 0x1, extracted from memory dump
is_composite = [
    0x0001, 0x0001, 0x0000, 0x0000, 0x0001, 0x0000, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0000, 0x0001, 0x0001,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0000,
    0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001, 0x0001,
    0x0001, 0x0001, 0x0001, 0x0000, 0x0001, 0x0001, 0x0001, 0x0001
]

reference = bytes.fromhex("""
cc b0 e7 7b bc c0 ee 3a fc 73 81 d0 7a 69 84 e2
48 e3 d7 59 11 6b f1 b3 86 0b 89 c5 bf 53 65 65
f0 ef 6a bf 08 78 c4 2c 99 35 3c 6c dc e0 c8 99
c8 3b ef 29 97 0b b3 8b cc 9d fc 05 1b 67 b5 ad
15 c1 08 d0 45 45 26 43 45 6d f4 ef bb 49 06 ca
73 6b bc e9 50 97 05 e5 97 d3 b5 47 2b ad 25 8b
ae af 41 e5 d8 14 f4 83 e6 f0 c0 98 0a ac a1 95
f5 b5 d3 53 f0 97 ef 9d d4 3b 3b 0b e7 17 07 1f
6c f1 1e 44 92 b2 57 07 b7 36 8f 53 c9 ea 10 90
62 df 1d 07 b3 71 53 61 1a 2b 78 bf c1 b5 c6 3b
ea 2b 44 17 a0 84 ca 8f b7 3b 38 2f e8 73 84 ad
44 ef f8 ad 8c 1f ea 7f cd c5 b3 49 05 03 95 a7
44 b5 91 69 f8 95 6c e5 87 53 4e 47 92 be 80 d0
80 1d ad f1 3d e3 df 35 61 f1 e7 0d 71 c5 02 4f
20 5e a2 8b c4 61 32 0f a8 be 7e 29 d1 6d 2a d9
55 47 07 83 ea 2b 79 95 4f 3d a3 11 dd c1 1d 89
""".replace('\n', ' '))

checkpoints = list(bytes.fromhex('7d ff 51 b7 53 3f f1 75 1f'))

start = 0x11

assert len(is_composite) == 256
assert len(reference) == 256

if len(sys.argv) >= 2 and sys.argv[1] == '-fancy': # Require a terminal capable of recognizing ANSI escape sequences
    print()
    for i in range(256):
        v = is_composite[reference[i]]
        if v:
            print('\x1b[7m', end='')
        if i == start:
            print('\x1b[1m\x1b[31m*\x1b[0m', end=' ')
        elif i in checkpoints:
            order = checkpoints.index(i)
            print('\x1b[1m\x1b[32m' + str(order) + '\x1b[0m', end=' ')
            # assert not v
        else:
            print('.', end=' ')
        if v:
            print('\x1b[0m', end='')
        if i % 16 == 15:
            print('\x1b[7m. \x1b[0m') # extra border and newline
    print('\x1b[7m' + '. ' * 17 + '\x1b[0m')
else:
    for i in range(256):
        if i % 16 == 0:
            print() # newline
        v = is_composite[reference[i]]
        if i == start:
            print('*', end='')
        elif i in checkpoints:
            order = checkpoints.index(i)
            print(order, end='')
            assert not v
        elif v:
            print('#', end='')
        else:
            print('.', end='')

print()