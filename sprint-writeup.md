# Sprint &mdash; Google CTF 2020
**Author:** Kevin He  
**Team:** 3PAC  
**Challenge Category:** Reversing  
**Points:** 173  
**Attachments:** [`sprint.elf`](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/sprint.elf)  

> Sprint faster than this binary!

## Abstract

<!-- Describe a outline of steps needed to achieve this so people won't get bored reading it -->
I took a very roundabout way to approach this challenge, here are my steps:  
1. I Decompiled `sprint.elf` in Ghidra.
2. `sprint.elf` uses embedded "format strings instructions" to obfuscate its process. So I built my custom disassembler to transform the format strings into a custom intermediate assembly language.
3. I translated the intermediate assembly language into NASM-compatible x86-64 assembly, which simulates `sprint.elf` using x86 machine code (mostly instructions operating on 16-bit words) instead of format strings.
4. I assembled the generated code in NASM.
5. I decompiled the assembled binary in Ghidra.
6. I discovered that the binary is a maze puzzle and the password represents instructions to run it.

## A puzzling binary

Start off by opening the binary in Ghidra and performing an auto analysis as prompted. The first thing I notice is that it starts off with an `mmap` requesting the kernel to allocate some memory at virtual address `0x4000000` for it:
```c
mmap(0x4000000, 0x4000000, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
```

Programs don't usually request exact addresses. A correctly behaving program should not depend on the address a buffer is located, so this line already hints that the program may perform some low-level procedure, such as manipulating bits of pointers.

In Ghidra, I renamed the return pointer of `mmap` to `mem`. Since the code runs early in the program, there are probably a lot of free addresses, so the program should get its desired address `0x4000000`. By running the program in GDB debugger, I verified that `mem` is indeed `0x4000000`.

The binary then performs a series of steps
1. Copy a range of memory, which looks like a series of `printf` format strings delimited by null terminators (`'\0'`), into `mem`.
2. Ask for a password with a maximum of 255 characters and store it `0xe000` bytes into the buffer `mem` (at `mem + 0xe000`).
3. Sets a local `char *` variable to `mem`, which I named `fstring`, and a `short *` variable to `mem`, which I named `r1`.
4. Run `sprintf((char *) 0x6000000, fstring, "", 0, &fstring, (char *) 0x6000000, *r1, r1, &r1, r2, &r2, ..., &ra)` repeatedly until `fstring == mem + 0xfffe`. `sprintf` is like `printf` except that it prints the output to a buffer (in this case a fixed memory location deep inside the `mmap`'d region: `0x6000000`) instead of `stdout`. The empty string `""`, or a pointer to a single null character, is the first variadic argument used by format strings. It is followed by a lot of arguments, most of them in a value/reference pattern.
5. If any of the first 2 bytes at `mem + 0xe800` is nonzero, then print the flag as a string located at `mem + 0xe800`. Otherwise, the program silently quits.

On first sight, it seems that step 4 will run into an infinite loop since `fstring` is set to `mem` so can never be equal to `mem + 0xfffe`. By when I actually ran this binary with random password inputs, it seems that there's a noticeable pause between entering the password and the program exitting.

## Moment of Insight

What caused the program to escape the loop and exit? To answer this question, I revised some of my assumptions. Since the `printf` family of functions (including `sprintf`) are output functions, in regular usage they read from memory and variables rather than modifying them. That's true for all format specifiers (`%s`, `%c`, `%d`, etc.) except a less known one `%n`. The `printf(3)` man page specifies that `%n` writes the number of characters written so far into an integer pointer specified in the corresponding function argument. From doing pwn challenges I learned that this format string specifier is commonly used to write arbitrary content to arbitrary memory locations when an attacker have control over the format string.

Since the program eventually breaks out of the loop, it must have modified the pointer `fstring`, looking at the `sprintf` line I indeed saw that it reference (`&fstring`) is passed as the third variadic argument, allowing the value of `fstring` to be modified.

Inspecting the format strings, I see `%hn` instead of `%n`. `h` is a modifier that tells `%n` that the argument passed points to a 16-bit integer (`short`) rather than a 32-bit `int`. This means that `sprintf` will only overwrite 2 bytes at `fstring`. In a little endian system like Intel, this only modifies the least significant 16 bits, or the last 4 hex digits, of `fstring`.
This diagram illustrates how the layout of `fstring`, `%hn` modifies `YY` and `ZZ`:

```
fstring = 0x400YYZZ
fstring in memory (hex): ZZ, YY, 00, 04
```

Modifying only 2 bytes makes sense because if the upper bits (the `0x400` prefix) are modified `fstring` would likely point to an invalid memory location, which will crash `sprintf` with a segfault.

## Demystifying the list of format strings

The pause between entering the password and exiting indicates that probably a lot of computation is done while `sprintf` processes the format strings. In [`read-fstrings.py`](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/read-fstrings.py), I used the null byte `'\0'` to split the format strings into a list so it can be analyzed more easily.

The first 2 entries of format string (as well as their offsets from `mem` in decimal) is presented here (the full list can be found at [`instructions-fstr.txt`](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/instructions-fstr.txt)):
```
00000:  %1$00038s%3$hn%1$65498s%1$28672s%9$hn
00038:  %1$00074s%3$hn%1$65462s%1$*8$s%7$hn
```

Having `N$` immediately after `%` and `*` means that the format string specifier is explicitly referring to the `N`th variadic argument. For example, `%1$s` would print the first variadic argument as a string, and `%3$n` would write the number of characters written to pointer passed by the third argument.

<!-- I noticed that the first line writes 38 characters (an empty string padded to a width of 38) into `0x6000000` and that the number of characters written (38) is written into the 3rd variadic argument, which is the first 2 bytes of `&fstring`. This means that `fstring` is the program counter for the format string machine, and it is moved to the next instruction at `mem + 00038`. Therefore, in the next iteration of the loop `sprintf` "executes" the next format string instruction. -->

The format strings perform additions modulo 65536 (`0x10000`) by repeatedly accumulating the character counter (the number of characters written) with constant or variable values. Everytime the program writes the empty string `""` at a fixed (like `%1$00038s`) or variable (like `%1$*8$s`) width, the character counter advances. And it writes the lowest 16-bit of the character counter (or the number of characters written modulo 65536) to the `N`th variadic argument using `%N$hn`. Every line has at least one occurrence of `%3$hn`, or writing to `fstring`. The purpose of this is to change the "program counter" to point to another format string, which is usually the next format string unless there's a conditional or unconditional jump.

For more details on format string syntax I recommend reading the `printf(3)` man page or this [cppreference.com page on `printf`](https://en.cppreference.com/w/c/io/fprintf). The general idea is that the format string describes a mini-assembly language capable of 16-bit indirect addressing (basically pointer dereference) within the first 65536 bytes of `mem`, conditional jumps based on byte values, unconditional jumps, and exit (by jumping to `mem + 0xfffe`, which terminates the `sprintf` loop). The local variables in `main` passed as a long chain of variadic arguments to `sprintf` are the format string machine's 16-bit registers (which I named from `r1` to `r7`). There is one register at the end (I named it `ra`) which is only written with values from `0` to `5` and never read. It is there probably to aid debugging.

## Transpiling the format strings to x86-64 assembly

To make analyzing the format string instructions easier, I wrote a [disassembler](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/disassemble.py) for it. The result is in [listing.txt](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/listing.txt). But after seeing the assembly, I realized that even the disassembled code is probably too difficult to analyze without aid from reverse engineering tools like Ghidra. But Ghidra can only analyze existing instruction set architectures, not custom ones like this. So I decided to take a more drastic approach to this: converting it to x86 machine code. Since these instruction all operate on 16-bit "registers" (arithmetic operations expect the integer wrap-around behavior in 16-bit mode, or arithmetic modulo 65536), the best translation is to use 16-bit x86 registers in place of format string registers and only use 64-bit registers to perform indirect addressing (access memory in `mem`). And I mapped `r1` to `r7` to `ax, bx, cx, dx, bp, di, si` respectively. `ra` is represented as a variable in memory. `sp` is not used since it is not general purpose. It is the lower bits of the stack pointer and should not be modified.

To build a x86-64 assembly simulating the `sprint.elf`, I first modified the disassembler to generate assembler friendly labels as well as making the output more machine parsable (See `disassemble-machine.py`). Then I wrote another script `procasm.py` to make modifications to the pseudo-assembly so it can be compiled in NASM and run correctly on x86-64. It translates instructions like `mov r1, r6 + 28672` to `mov ax, di; add ax, 28672` and adds memory offsets for indirect addressing (Ex. `mov [r1], r4` to `mov word [mem + rax], dx`)

## Building and analyzing the new binary

I assembled the program in NASM (for commands see [Makefile](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/Makefile)) and ran it once to make sure it doesn't crash. I then loaded the binary in Ghidra \[TBD\]: (source code modified to increase clarity, such as turning characters to integer literals)

```c
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void main(void)

{
  bool bVar1;
  char cVar2;
  short sVar3;
  ushort uVar4;
  short sVar5;
  short sVar6;
  char cVar7;
  
  DAT_00417000 = 1;
  DAT_00417002 = 1;
  sVar3 = 2;
  /* Sieve of Eratosthenes, builds a 8-bit primality table at (mem + 0x7000) */
  do {
    if ((char)*(undefined2 *)(mem + (ushort)(sVar3 * 2 + 0x7000)) == '\0') {
      DAT_0041ffef = sVar3 * 2;
      while ((char)(_DAT_0041ffef >> 8) == '\0'
                    /* WARNING: Ignoring partial resolution of indirect */) {
        *(undefined2 *)(mem + (ushort)(DAT_0041ffef * 2 + 0x7000)) = 1;
        DAT_0041ffef = DAT_0041ffef + sVar3;
      }
    }
    sVar3 = sVar3 + 1;
  } while ((char)sVar3 != '\0');
  uVar4 = 0xe000; // password: mem + 0xe000
  cVar7 = 0;
  while ((char)*(undefined2 *)(mem + uVar4) != '\0') {
    cVar7 = cVar7 + -1;
    uVar4 = uVar4 + 1;
  }
  if (cVar7 == 2) { // strlen(password) == 254, 254 = 256 - 2
    sVar6 = 0;
    sVar3 = 0;
    bVar1 = true;
    _addr_ra = 0;
    uVar4 = DAT_0041f100; // = 0x11, initial location in the maze: (1, 1)
    while (cVar7 = (char)*(undefined2 *)(mem + (ushort)(sVar6 + 0xe000)), cVar7 != '\0') {
      sVar6 = sVar6 + 1; // moves: u=up, r=right, d=down, l=left
      if (cVar7 == 'u') {
        sVar5 = -0x10; // decrease Y coordinate
      }
      else {
        if (cVar7 == 'r') {
          sVar5 = 1; // increase X coordinate
        }
        else {
          if (cVar7 == 'd') {
            sVar5 = 0x10; // increase Y coordinate
          }
          else {
            if (cVar7 == 'l') {
              sVar5 = -1; // decrease X coordinate
            }
            else {
              bVar1 = false; // fail, bad character.
              sVar5 = 0;
              _addr_ra = 1;
            }
          }
        }
      }
      uVar4 = uVar4 + sVar5;
      _DAT_0041ffef = _DAT_0041ffef & 0xff0000 | (uint3)uVar4;
      if ((char)((uint3)uVar4 >> 8) != '\0') { // upper 8-bit of uVar4 (coordinate) should always be 0, otherwise the Y coordinate has overflown/underflown
        _addr_ra = 4; // Y coordinate out of 0x0 - 0xf range, fail
        return;
      }
      _DAT_0041ffef = (uint3)(byte)*(ushort *)(mem + (ushort)(uVar4 - 0x1000));
      DAT_0041ffef = *(ushort *)(mem + (ushort)(uVar4 - 0x1000)) & 0xff; // access a 8-bit number in a char[256] (or char[16][16]) table at (mem + 0xf000) with coordinate as the index
      if ((char)*(undefined2 *)(mem + (ushort)(DAT_0041ffef * 2 + 0x7000)) == '\0') { // check whether the 8-bit number is prime using the primality table at (mem + 0x7000), prime: passable block, composite: wall
        if ((char)((char)*(undefined2 *)(mem + (ushort)(sVar3 - 0xefd)) + (char)uVar4) == '\0') { // reached a checkpoint
          sVar3 = sVar3 + 1; // increase checkpoint counter by 1
        }
      }
      else {
        bVar1 = false; // fail, hit a wall block
        _addr_ra = 2;
      }
    }
    if (bVar1) {
      if ((char)sVar3 == 9) { // must get all 9 "stars" (visit 9 locations in order)
        sVar6 = 0;
        sVar3 = 0;
        do { // decrypt the 39-character flag
          if ((char)sVar6 == 39) {
            *(undefined2 *)(mem + (ushort)(sVar6 + 0xe800)) = 0;
            return;
          }
          cVar7 = 4;
          sVar5 = 0;
          do {
            sVar5 = sVar5 * 4;
            cVar2 = (char)*(undefined2 *)(mem + (ushort)(sVar3 + 0xe000));
            if (cVar2 != 'u') {
              if (cVar2 == 'r') {
                sVar5 = sVar5 + 1;
              }
              else {
                if (cVar2 == 'd') {
                  sVar5 = sVar5 + 2;
                }
                else {
                  if (cVar2 != 'l') {
                    DAT_0041e800 = 0;
                    return;
                  }
                  sVar5 = sVar5 + 3;
                }
              }
            }
            sVar3 = sVar3 + 1;
            cVar7 = cVar7 + -1;
          } while (cVar7 != 0);
          *(undefined2 *)(mem + (ushort)(sVar6 + 0xe800)) =
               *(undefined2 *)(mem + (ushort)(sVar6 - 0xef4));
          *(short *)(mem + (ushort)(sVar6 + 0xe800)) =
               *(short *)(mem + (ushort)(sVar6 + 0xe800)) + sVar5;
          sVar6 = sVar6 + 1;
        } while( true );
      }
      _addr_ra = 3;
    }
  }
  else {
    _addr_ra = 5;
  }
  DAT_0041e800 = 0;
  return;
}

```

### Prime finder using only additions and conditional jumps

The first loop describes assigns values to a `ushort[256]` array located at `mem + 0x7000`. At first I didn't realize what is going on in this loop. Since the result of this doesn't depend on the input password, I just copied 256 `ushort` values from `mem + 0x7000` at program runtime using gdb. After inspecting the array I discovered that this block of code assigns `0x0001` to composite indices of the array, and leave prime indices to the default `0x0000` value. Despite the rather limited instruction set, the code implements the Sieve of Eratosthenes! An illustration of how the code works is in this animation:

![gradually sieving out composite numbers that is a multiple of primes up to sqrt(n)](assets/Sieve_of_Eratosthenes_animation.svg)

The prime table built in this step will be used later on.

### Navigating my way through the code maze

The code then checks that the length of the password (Located at `mem + 0xe000`) and makes sure that it is 254. It then iterates through every character of the password. The only valid characters are `u`, `d`, `r`, and `l`. Doing a lot of reversing challenges, maze navigation is arguably one of the common themes, so my mind yells up, down, right, and left upon seeing these!

`uVar4` (or register `dx`/`r4`) keeps the current coordinate of the maze player in its lower byte (the upper byte should must be zero to pass the challenge). Its format is `0xYX`, where `Y` is the y coordinate, with higher values going down, and `X` is the x coordinate, with higher values going to the right. It is initialized to `0x11`, meaning the maze runner start at coordinate (X=1, Y=1) near the top left corner.

```
 |0 |1 |2 |...|E |F -→ X
0|00|01|02|...|0E|0F
1|10|11|12|...|1E|1F
2|20|21|22|...|2E|2F
.|..|..|..|...|..|..
E|E0|E1|E2|...|EE|EF
F|F0|F1|F2|...|FE|FF
↓
Y
```

Since the format string instructions set only support additions mod 65536 (with subtractions by `n` simulated by addition of `(65536 - n)` mod 65536) and no bitwise operators, maze moves parallel to the Y and X axes are performed by adding or subtracting `0x10` or `0x1` to the current location `uVar4`. This technically allows overflow/underflow of the X coordinate (moving over the left or right edge) outside of the range `0x0` to `0xf` to increment or decrement the Y coordinate, but the Google CTF Team has put that into account by adding a "security fence" (a straight vertical line of walls) along the leftmost edge of the entire maze, which I would show later on.

### Render the maze

When initially listing the binary instructions, I discovered a blob of binary data at `mem + 0xf000`. And it turns out that the 256 bytes after this describes a maze in a rather obfuscated way: a wall is located at coordinate `i` if and only if `mem + 0xf000 + i` is composite (not prime). This is where the code looks up the prime table built earlier.

Obviously, the code checks that the moves from the input password does not cause the maze runner to bump into walls, but it also requires that the runner reach 9 checkpoints in order. In the binary the bytes are `83 01 af 49 ad c1 0f 8b e1`, but the codechecks that `(<current location> + <next checkpoint byte>) % 256 == 0x0`, so the actual locations are negated (`actual = 256 - raw`), so the actual locations are `7d ff 51 b7 53 3f f1 75 1f`.

Using only raw data found in the binary and some transformations, the script [demangle-maze.py](https://github.com/kevin-he-01/gctf2020-sprint-writeup/blob/master/demangle-maze.py) prints a nice maze picture:

```
################
#*#.....#......8
#.#.#####.######
#.......#.#.#..5
#.#####.#.#.#.##
#2#4#...........
###.###.#######.
#...#7..#...#0..
#.#####.###.####
#.......#.#...#.
#.#.#####.#.###.
#.#.#.#3#.......
#.###.#.#.#.####
#.........#.....
###.#.#####.#.##
#6..#.#.....#..1
```

You have to go from the asterisk `*` to `0` to `1` to `2` to ... and end at `8`. It turns out the shortest way to achieve this requires `254` steps, which means there's exactly one possible password. That has to be the case in order to deterministically decrypt the flag.

### Finale

I didn't use any scripts to solve this maze, since it is trivial to solve by hand as long as it is done carefully:

```
$ ./sprint.elf 
Input password:
ddrrrrrrddrrrrrrrrddllrruullllllllddddllllllddddrrrrrrrruurrddrrddrrlluulluullddlllllllluuuurrrrrruuuuuulllllldduurrrrrrddddddllllllddddrrrrrruuddlllllluuuuuurruuddllddrrrrrruuuurrrrrruurrllddllllllddddllllllddddrrddllrruulluuuurrrrrruullrruurruuuurrrrrr
Flag: CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}
```

## End Note
The Google CTF team is very creative in inventing its own Turing complete format string assembly language.

See Also: [My GitHub repository](https://github.com/kevin-he-01/gctf2020-sprint-writeup) on this writeup.
