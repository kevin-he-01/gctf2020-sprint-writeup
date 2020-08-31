#! /usr/bin/env python3
# Writes a listing of format string assembly to listing.txt
import traceback, sys, enum
from typing import List, Tuple, Optional, Union, Dict

listing = []

# format string chars use: s, c, hn

class Expression:
    def __str__(self):
        raise NotImplementedError

class RegType(enum.Enum):
    SPECIAL = 0
    ADDR = 1
    REGULAR = 2
    ADDR_PC = 3
    ADDR_RA = 4

# regnames = {1: 'addr_z', 2: 'z', 3: 'addr_pc', 4: 'output', 5: '(word [r1])', 22: '(qword [ra])', 23: 'ra'}
regnames = {1: 'addr_z', 2: 'z', 3: 'addr_pc', 4: 'output', 5: 'word [r1]', 22: 'ra', 23: 'addr_ra'}

class Register(Expression):
    def __init__(self, argn: int):
        self.argn = argn
        if argn in regnames:
            self.type = (RegType.SPECIAL if argn != 3 else RegType.ADDR_PC) if argn != 23 else RegType.ADDR_RA
            self.name = regnames[argn]
        else:
            offset = self.argn - 6
            assert offset >= 0
            self.type = RegType.ADDR if offset % 2 == 1 else RegType.REGULAR
            self.regnum = (offset // 2) + 1
            name = ('addr_r{}' if self.type == RegType.ADDR else 'r{}').format(self.regnum)
            self.name = name 
    
    def __str__(self): # TODO use special names like pc for a3 and addr_n, etc.
        # return 'a{}'.format(self.argn)
        # return 'a{}'.format(self.argn)
        return self.name

class Addable:
    # def add(self, n: Union[int, Register, ImmutableDirectValue]):
    def add(self, n):
        raise NotImplementedError
    def copyout(self): # To construct a ImmutableDirectValue
        raise NotImplementedError

class DirectValue(Addable):
# class DirectValue(Expression): # a buffer for ImmutableDirectValue
    def __init__(self):
        # self.val = []
        self.regs = []
        self.offset = 0
    
    def add(self, n):
        # if len(self.val) > 0 and isinstance(self.val[-1], int):
        #     self.val[-1] += n
        # else:
        #     self.val.append(n)
        if isinstance(n, int):
            self.offset += n
        elif isinstance(n, Register):
            self.regs.append(n)
        elif isinstance(n, ImmutableDirectValue):
            self.offset += n.offset # avoids race conditions by not allowing itself (mandate copy)
            self.regs.extend(n.regs) # self.regs may == n.regs
        else:
            raise RuntimeError('{} of type {}: bad type'.format(n, type(n)))
    
    def copyout(self):
        return self.regs[:], self.offset, None, None

class DualConstant(Addable):
    def __init__(self, condreg, ifzero: int, ifnotzero: int):
        self.condreg = condreg
        self.ifzero = ifzero
        self.ifnotzero = ifnotzero
    
    def add(self, n): # unconditional add
        if isinstance(n, int):
            self.ifzero += n
            self.ifnotzero += n
        else:
            raise RuntimeError('Unsupported type {}'.format(type(n)))
    
    def copyout(self):
        return [], self.ifzero, self.ifnotzero, self.condreg

class ImmutableDirectValue(Expression): # an addition of registers and numbers
    def __init__(self, dv: Addable):
        regs, offset, altoffset, condreg = dv.copyout()
        self.regs = regs
        self.offset = offset
        self.altoffset = altoffset
        self.condreg = condreg
    
    def __str__(self): # TODO: display reg as set like (ra * 2 + rb * 3) instead of ra + rb + ra + rb + rb
        if self.altoffset == None:
            offset = self.offset % 0x10000 # all registers are shorts
            if offset >= 0x8000: # 2's complement
                offset -= 0x10000
            if len(self.regs) == 0:
                return str(offset)
            regstr = ' + '.join(map(str, self.regs))
            if offset > 0:
                regstr += ' + {}'.format(offset)
            elif offset < 0:
                regstr += ' - {}'.format(-offset)
            return regstr
        else:
            condreg = self.condreg
            assert isinstance(condreg, Register)
            if len(self.regs) != 0:
                raise RuntimeError("Have not implemented regs and conditionals yet")
            condreg: Register
            return '{} if {} == 0 else {}'.format(self.offset % 0x10000, condreg, self.altoffset % 0x10000)

class IndirectValue(Expression):
    def __init__(self, contained: Expression):
        self.contained = contained
    
    def __str__(self):
        c = self.contained
        if isinstance(c, Register):
            c: Register
            if c.type == RegType.ADDR:
                return 'r{}'.format(c.regnum)
            elif c.type == RegType.ADDR_PC:
                return 'pc'
            elif c.type == RegType.ADDR_RA:
                return 'ra'
        return '[{}]'.format(self.contained)

# class Conditional(Expression):
#     def __init__(self, cond: Expression, ifzero: Expression, ifnotzero: Expression):
#         self.cond = cond
#         self.ifzero = ifzero
#         self.ifnotzero = ifnotzero

#     def __str__(self):
#         return '({} if {} == 0 else {})'.format(self.ifzero, self.cond, self.ifnotzero)

class Instruction:
    def __init__(self, name: str, operands: List[Expression]):
        self.name = name
        self.operands = operands
    
    def __str__(self):
        return '{} {}'.format(self.name, ', '.join(map(str, self.operands)))

commenttab = 50

class ListingEntry:
    def __init__(self, addr, instructions: List[Instruction], comments: str = ''):
        self.addr = addr
        self.instructions = instructions
        self.comments = comments

    def __str__(self):
        base = '{:05d}: {}'.format(self.addr, '; '.join(map(str, self.instructions)))
        if self.comments != '':
            base = base.ljust(commenttab)
            base += ' // {}'.format(self.comments)
        return base

special = "%2$c%4$s" # Conditional jump!

next_addr: Dict[int, int] = dict()

with open('instructions-fstr.txt') as instf:
    lastaddr = None
    for num, line in enumerate(instf):
        if line.endswith('\n'):
            line = line[:-1]
        colon = line.find(':')
        addr = int(line[:colon])
        # itype = line[colon + 2]
        if lastaddr != None:
            next_addr[lastaddr] = addr
        lastaddr = addr

with open('instructions-fstr.txt') as instf:
    for num, line in enumerate(instf):
        if line.endswith('\n'):
            line = line[:-1]
        parsei = -1
        ntoken = 0
        try:
            colon = line.find(':')
            addr = int(line[:colon])
            itype = line[colon + 2]
            if itype == ' ':
                ncharwritten = DirectValue()
                ncharwritten: Addable
                # condition = None
                # condition: Optional[Tuple[Register, ImmutableDirectValue]]
                condreg = None
                condreg: Optional[Register]
                comments = ''
                insts: List[Instruction] = []
                jump: Optional[Instruction] = None
                parsei = colon + 3
                while parsei < len(line):
                    # print(parsei) # verbose!
                    ntoken += 1
                    assert line[parsei] == '%'
                    if line[parsei:parsei+len(special)] == special:
                        # print('special pattern found: L{}: addr {}'.format(num+1, addr))
                        # ncharwritten.add(Conditional(condition[0], condition[1], ImmutableDirectValue(ncharwritten))) # *2 + 1
                        if condreg == None:
                            ncharwritten.add(ImmutableDirectValue(ncharwritten))
                        else:
                            immnchar = ImmutableDirectValue(ncharwritten)
                            assert len(immnchar.regs) == 0
                            # ncharwritten.add(DualConstant(condreg, 0, immnchar.offset))
                            ncharwritten = DualConstant(condreg, 0, immnchar.offset)
                            ncharwritten.add(immnchar.offset)
                        ncharwritten.add(1) # write one null char
                        parsei += len(special)
                        # comments += 'special pattern. '
                        # comments += 'conditional jump. '
                    else:
                        parsei += 1 # skip over %
                        end = line.find('$', parsei)
                        argn = int(line[parsei:end])
                        parsei = end + 1 # skip over $
                        # parsei = line.find('%')
                        if line[parsei] == 'c':
                            # assert condition == None, 'double condition!' # condition only checks for lowest 8 bits
                            assert condreg == None, 'double condition!' # condition only checks for lowest 8 bits
                            immnchar = ImmutableDirectValue(ncharwritten)
                            assert immnchar.altoffset == None
                            assert immnchar.offset == 0
                            assert len(immnchar.regs) == 0
                            condreg = Register(argn)
                            # condition = (Register(argn), ImmutableDirectValue(ncharwritten)) # if (byte)register is 0, then pc = second
                            # comments += 'writes char value of {} at (0x6000000 + {}). '.format(Register(argn), ImmutableDirectValue(ncharwritten))
                            ncharwritten.add(1)
                            parsei += 1
                        # elif line[parsei] == 's':
                        elif line[parsei] == 'h':
                            assert line[parsei + 1] == 'n'
                            reg = Register(argn)
                            inst = Instruction('mov', [IndirectValue(reg), ImmutableDirectValue(ncharwritten)])
                            if reg.type == RegType.ADDR_PC:
                                # comments += str(inst)
                                if isinstance(ncharwritten, DualConstant):
                                    ncharwritten: DualConstant
                                    ifz, ifnz = map(lambda n: n % 0x10000, [ncharwritten.ifzero, ncharwritten.ifnotzero])
                                    assert ifz == next_addr[addr], 'Invalid next address: actual {} != expected {}'.format(ifz, next_addr[addr])
                                    jump = Instruction('jnz', [ncharwritten.condreg, ifnz])
                                elif isinstance(ncharwritten, DirectValue):
                                    ncharwritten: DirectValue
                                    offset = ncharwritten.offset % 0x10000
                                    if not (ncharwritten.regs == [] and offset == next_addr[addr]):
                                        if ncharwritten.regs == [] and offset == 0xfffe: # -2
                                            jump = Instruction('ret', []) # end
                                        else:
                                            jump = Instruction('jmp', [ImmutableDirectValue(ncharwritten)])
                                # jump = Instruction('jmp')
                            else:
                                insts.append(inst)
                            # if condition == None:
                            #     insts.append(Instruction('mov', [IndirectValue(Register(argn)), ImmutableDirectValue(ncharwritten)]))
                            # else:
                            #     insts.append(Instruction('mov', [IndirectValue(Register(argn)), Conditional(condition[0], condition[1], ImmutableDirectValue(ncharwritten))]))
                            parsei += 2
                        elif line[parsei].isnumeric() or line[parsei] == '*':
                            assert argn == 1, 'Writing string not sourced from space pool!'
                            if line[parsei].isnumeric():
                                end = line.find('s', parsei)
                                ncharwritten.add(int(line[parsei:end]))
                                parsei = end
                            else:
                                parsei += 1 # skip over *
                                end = line.find('$', parsei)
                                ncharwritten.add(Register(int(line[parsei:end])))
                                parsei = end + 1
                            assert line[parsei] == 's'
                            parsei += 1
                        else:
                            raise RuntimeError('{} is not a recognized character after %<number>$'.format(line[parsei]))
                if jump != None:
                    insts.append(jump)
                listing.append(ListingEntry(addr, insts, comments))
            elif itype == '#':
                print('L{}: addr {}: directive ignored'.format(num+1, addr))
        except Exception:
            # traceback.print_last()
            print('Parser error @ {}:{} parsing {}th token'.format(num+1, parsei, ntoken))
            traceback.print_exc()
            sys.exit(1)

with open('listing.txt', 'w') as lf:
    lf.writelines(map(lambda e: str(e) + '\n', listing))

