points = bytes.fromhex("83 01 af 49 ad c1 0f 8b e1")

print('In list format:', list(points))
print('After negation:', bytes(map(lambda b: 256-b, points)).hex())
