# Files related to my writeup for Sprint from Google CTF 2020
- [`read-fstrings.py`](./read-fstrings.py): Generate assembly listing and write to `instructions-fstr.txt`, which is necessary for all later steps
- [`disassemble.py`](./disassemble.py): Generate human readable assembly listing for the format strings
## Steps for x86 binary generation
1. [`disassemble-machine.py`](./disassemble-machine.py): Generate pseudo x86 assembly
2. [`procasm.py`](./procasm.py): Generate NASM assembly source
3. [`Makefile`](./Makefile): run `make` to generate a simulated x86-64 binary (`simulate.out`) that does the same thing as `sprint.elf`, the challenge file.
