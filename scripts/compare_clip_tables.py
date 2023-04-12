"""
Script that compares clip tables output by the Nighthawk detector with
clip tables exported from Vesper.

The script compares both standard, comma-delimited CSV files as well as
Raven selection tables, which can be described as tab-delimited CSV files.

The first two values of each row of the files (except for the header rows)
are times, which the script only requires be the same after rounding to
the nearest millisecond. The other values are required to be identical.

The goals here are to:

    1. Verify that all clip information output by Nighthawk is included
       in the Vesper clips created by the `vesper_nighthawk` Vesper plugin.

    2. Demostrate that Vesper can export Nighthawk clips to both standard,
       comma-delimited CSV files and Raven selection table files that are
       equivalent to those produced by Nighthawk itself.
"""


from pathlib import Path
import csv


TEST_DATA_DIR_PATH = \
    Path(__file__).parent.parent / 'test_inputs' / 'Clip Table Comparison'
NIGHTHAWK_FILE_NAME_STEM = 'Ithaca_2021-10-03_06.00.00_Z_detections'
VESPER_FILE_NAME_STEM = 'Vesper Clip Table'
FILE_NAME_EXTENSIONS = ('.csv', '.txt')
CSV_FORMAT_PARAMS = {
    '.csv': {},
    '.txt': {'delimiter': '\t'}
}
TIME_COLUMN_NUMS = frozenset((1, 2))


def main():
    for extension in FILE_NAME_EXTENSIONS:
        file_path_a = get_file_path(NIGHTHAWK_FILE_NAME_STEM, extension)
        file_path_b = get_file_path(VESPER_FILE_NAME_STEM, extension)
        compare_csv_files(file_path_a, file_path_b)


def get_file_path(stem, extension):
    file_name = stem + extension
    return TEST_DATA_DIR_PATH / file_name


def compare_csv_files(file_path_a, file_path_b):

    compare_row_counts(file_path_a, file_path_b)
    compare_file_contents(file_path_a, file_path_b)

    print(
        f'The files "{file_path_a.name}" and "{file_path_b.name}" '
        f'contain identical headers and equivalent clips.')


def compare_row_counts(file_path_a, file_path_b):

    with open(file_path_a, newline='') as file_a, \
            open(file_path_b, newline='') as file_b:
        
        reader_a = csv.reader(file_a)
        reader_b = csv.reader(file_b)

        count_a = count_rows(reader_a)
        count_b = count_rows(reader_b)

        assert count_a == count_b, 'Files have different numbers of rows.'


def count_rows(reader):
    count = 0
    for _ in reader:
        count += 1
    return count


def compare_file_contents(file_path_a, file_path_b):

    with open(file_path_a, newline='') as file_a, \
            open(file_path_b, newline='') as file_b:
        
        extension = file_path_a.suffix
        format_params = CSV_FORMAT_PARAMS[extension]

        reader_a = csv.reader(file_a, **format_params)
        reader_b = csv.reader(file_b, **format_params)

        compare_headers(reader_a, reader_b)
        compare_bodies(reader_a, reader_b)
        

def compare_headers(reader_a, reader_b):
    header_a = reader_a.__next__()
    header_b = reader_b.__next__()
    assert header_a == header_b, 'File headers differ.'


def compare_bodies(reader_a, reader_b):
    for i, clips in enumerate(zip(reader_a, reader_b)):
        row_num = i + 2
        compare_clips(row_num, *clips)


def compare_clips(row_num, clip_a, clip_b):
    for i, values in enumerate(zip(clip_a, clip_b)):
        col_num = i + 1
        compare_values(row_num, col_num, *values)


def compare_values(row_num, col_num, value_a, value_b):

    def create_error_message(name):
        return (
            f'At row {row_num} column {col_num}, {name} {value_a} differs '
            f'from {name} {value_b}.')

    if col_num in TIME_COLUMN_NUMS:
        time_a = round_time(value_a)
        time_b = round_time(value_b)
        assert time_a == time_b, create_error_message('time')
    
    else:
        assert value_a == value_b, create_error_message('value')
        

def round_time(value):
    seconds = float(value)
    millis = int(round(1000 * seconds))
    return millis / 1000


if __name__ == '__main__':
    main()
