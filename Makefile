build:
	nasm -f elf64 output.nasm -o output.elf
	ld -Tdata=0x410000 -o simulate.out output.elf
