#! /usr/bin/env python3
import traceback, sys
regmap = {'r1': 'ax', 'r2': 'bx', 'r3': 'cx', 'r4': 'dx', 'r5': 'bp', 'r6': 'di', 'r7': 'si'}
regmap8 = {'r1': 'al', 'r2': 'bl', 'r3': 'cl', 'r4': 'dl', 'r5': 'bpl', 'r6': 'dil', 'r7': 'sil'}

# password = b'a' * 255 # TODO, change

def convert(val, reg8=False):
    rmap = regmap8 if reg8 else regmap
    # if val == '[ra]':
    if val == 'ra':
        return 'word [addr_ra]'
    if val == 'word [r1]' or val == '[r1]':
        # return 'word [mem + eax]'
        return 'word [mem + rax]'
    if val[0] == '[':
        assert val[-1] == ']'
        # return 'word [e' + convert(val[1:-1]) + ']' # 32ism
        return 'word [r' + convert(val[1:-1]) + ']'
    elif val[0].isdigit():
        return val
    else:
        return rmap[val]

memlen = 0xf134

with open('sprint.elf', 'rb') as spf:
    spf.seek(0x2020)
    membin = spf.read(memlen)
    assert len(membin) == memlen, len(membin)

with open('pseudoasm.txt') as pa, open('output.nasm', 'w') as outa:
    outa.write("""global _start
read equ 0
write equ 1
exit equ 60
pwlen equ 255`
flaglen equ 39
section .rodata
prompt db 'Input password:', 0xa
plen equ $ - prompt
give_flag db 'Flag: '
gflen equ $ - give_flag
section .data
mem db """)
    # with open('sprint.elf') as spf:
    #     spf.seek(0x2020)
    #     outa.write("{}, ")
    outa.write(",".join(map(hex, membin)) + "\n")
    outa.write("times {} db 0x0\n".format(0x10000 - memlen))
    outa.write("""addr_ra dw 0
pswd equ (mem + 0xe000)
flag_addr equ (mem + 0xe800)
section .text
_start:
mov rdx, plen
mov rsi, prompt
mov rdi, 1
mov rax, write
syscall
mov rdx, pwlen
mov rsi, pswd
mov rdi, 0
mov rax, read
syscall
cmp rax, 0
jle rfail ; EOF or negative is fail
cmp byte [pswd + rax - 1], 0x0a ; replace \\n with zero byte
jne skip
mov byte [pswd + rax - 1], 0x0
skip:
call main ; call actual computation part
cmp word [flag_addr], 0
je fail
mov rdx, gflen ; Print flag
mov rsi, give_flag
mov rdi, 1
mov rax, write
syscall
mov rdx, flaglen
mov rsi, flag_addr
mov rdi, 1
mov rax, write
syscall
mov rdi, 0 ; exit successfully
jmp final
rfail:
mov rdi, 3
jmp final
fail:
mov rdi, 1
final:
mov rax, exit
syscall
main:
xor rax, rax
xor ebx, ebx
xor ecx, ecx
xor edx, edx
xor esi, esi
xor edi, edi
xor ebp, ebp
""")
    try:
        for lnum, line in enumerate(pa):
            if line.endswith('\n'):
                line = line[:-1]
            if line.endswith(':') or line.startswith('ret'): # keep as is
            # if line.endswith(':'): # keep as is
                outa.write(line + '\n')
            elif line.startswith('mov'):
                comma = line.find(',')
                leftop = line[4:comma]
                rightops = line[comma + 2:].split(' + ')
                # if rightops == ['word [r1]']:
                #     outa.write('mov {}, word [ax]\n'.format(leftop))
                # else:
                assert len(rightops) > 0
                outa.write('mov {}, {}\n'.format(convert(leftop), convert(rightops[0])))
                for i in range(1, len(rightops)):
                    outa.write('add {}, {}\n'.format(convert(leftop), convert(rightops[i])))
            elif line.startswith('jnz'):
                comma = line.find(',')
                regcond = line[4:comma]
                addr = line[comma + 2:]
                outa.write('cmp {}, 0\njne {}\n'.format(convert(regcond, reg8=True), 'a_{:05d}'.format(int(addr))))
            elif line.startswith('jmp'):
                addr = int(line[4:])
                outa.write('jmp {}\n'.format('a_{:05d}'.format(addr)))
            else:
                raise RuntimeError('Unknown line: {}'.format(line))
    except Exception:
        print('Parser error @ {}'.format(lnum+1))
        traceback.print_exc()
        sys.exit(1)
