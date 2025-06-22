import csv
import io
import random
import sys

def shuffle(input_file, output_file):
    """
    :param input_file: input CSV file object
    :param output_file: output CSV file object
    """
    csv_reader = csv.reader(input_file)
    rows = list(csv_reader)
    random.shuffle(rows)
    writer = csv.writer(output_file)
    writer.writerows(rows)

if __name__ == '__main__':
    csv_input = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', newline='')
    csv_output = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='')
    shuffle(input_file=csv_input, output_file=csv_output)
