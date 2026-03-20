#Requires species.dat in the same directory grabbed from the Infinite Fusion game files. This script reads the Ruby Marshal format and extracts species data into a CSV file.

import struct
import csv

class MarshalParser:
    def __init__(self, data):
        self.data = data
        self.pos, self.symbols, self.objects = 0, [], []

    def read_byte(self):
        b = self.data[self.pos]; self.pos += 1
        return b

    def read_int(self):
        b = struct.unpack('b', bytes([self.read_byte()]))[0]
        if 5 <= b <= 127: return b - 5
        if -128 <= b <= -5: return b + 5
        size, res = b, 0 if b > 0 else -1
        for i in range(abs(size)):
            if size > 0: res |= self.read_byte() << (8 * i)
            else: res &= ~(0xff << (8 * i)); res |= self.read_byte() << (8 * i)
        return res

    def read_symbol(self):
        b = self.read_byte()
        if b == 0x3a:
            s = self.data[self.pos:self.pos+self.read_int()].decode('utf-8', errors='replace')
            self.pos += len(s); self.symbols.append(s); return s
        return self.symbols[self.read_int()]

    def read_object(self):
        t = self.read_byte()
        if t in (0x3a, 0x3b): self.pos -= 1; return self.read_symbol()
        if t == 0x22: s = self.data[self.pos:self.pos+self.read_int()].decode('utf-8'); self.pos += len(s); self.objects.append(s); return s
        if t == 0x69: return self.read_int()
        if t == 0x5b: # Array
            arr = []; self.objects.append(arr)
            for _ in range(self.read_int()): arr.append(self.read_object())
            return arr
        if t == 0x7b: # Hash
            h = {}; self.objects.append(h)
            for _ in range(self.read_int()): k, v = self.read_object(), self.read_object(); h[k] = v
            return h
        if t == 0x6f: # Object
            obj = {'_class': self.read_symbol()}; self.objects.append(obj)
            for _ in range(self.read_int()): obj[self.read_symbol()] = self.read_object()
            return obj
        if t == 0x30: return None
        if t == 0x54: return True
        if t == 0x46: return False
        if t == 0x49: v = self.read_object(); [ (self.read_symbol(), self.read_object()) for _ in range(self.read_int()) ]; return v
        if t == 0x40: return self.objects[self.read_int()]
        return None

# Execution
with open('species.dat', 'rb') as f:
    raw = f.read()
parser = MarshalParser(raw)
if parser.read_byte() == 4 and parser.read_byte() == 8:
    root = parser.read_object()
    # Process 'root' dictionary and write to CSV...