import argparse
import csv
import io
import sys
from enum import Enum

class Picker(Enum):
    HEAD = "head"
    TAIL = "tail"

    def __str__(self):
        return self.value

    def pick(self, elements, number):
        match self:
            case Picker.HEAD:
                return elements[:number]
            case Picker.TAIL:
                return elements[-number:]
            case _:
                raise NotImplementedError(f"pick() for {self.name} not implemented")

def pick(input_file, output_file, picker, number):
    csv_reader = csv.reader(input_file)
    rows = list(csv_reader)
    picked_rows = picker.pick(rows, number)
    writer = csv.writer(output_file)
    writer.writerows(picked_rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pick CSV rows')
    parser.add_argument('picker', type=Picker, choices=list(Picker), help='Picking algorithm')
    parser.add_argument('number', type=int, help='Number of rows to pick up')
    args = parser.parse_args()

    csv_input = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', newline='')
    csv_output = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='')
    pick(csv_input, csv_output, args.picker, args.number)
