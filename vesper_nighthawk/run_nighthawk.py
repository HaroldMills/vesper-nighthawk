"""Script that runs the Nighthawk NFC detector for Vesper."""


from argparse import ArgumentParser, ArgumentTypeError, BooleanOptionalAction
from collections import namedtuple, OrderedDict
from pathlib import Path
import csv
import json
import sys

import librosa
import nighthawk as nh


# RESUME:
# * Simplify process_detections.
# * Ensure that detection start indices are unique.


'''
Add "Interval Bounds Uniqueness Offset" annotation if start and end
indices were offset to ensure start time uniqueness. Annotation value
is integer offset that was added. Saving the offset will enable the
offsets to be undone later if we remove the current clip uniqueness
constraint.
'''

    
JSON_FILE_HEADER = '''
{
    "detections": [
'''.lstrip()


JSON_FILE_TRAILER = '''
    ]
}
'''.lstrip('\n')


def main():
    
    args = parse_args()
    
    # nh.process_files(
    #     [args.input_file_path],
    #     hop_duration=args.hop_duration,
    #     threshold=args.threshold,
    #     merge_overlaps=args.merge_overlaps,
    #     output_dir_path=args.output_dir_path)

    process_detections(args.input_file_path, args.output_dir_path)


def parse_args():
    
    parser = ArgumentParser()
    
    parser.add_argument(
        'input_file_path',
        type=Path,
        help='path of audio file on which to run detector.')
    
    parser.add_argument(
        '--hop-duration',
        help=(
            f'the hop duration in seconds, a number in the range '
            f'(0, {nh.MODEL_INPUT_DURATION}]. (default: 0.2)'),
        type=parse_hop_duration,
        default=nh.DEFAULT_HOP_DURATION)    
    
    parser.add_argument(
        '--threshold',
        help='the detection threshold, a number in [0, 100]. (default: 50)',
        type=parse_threshold,
        default=nh.DEFAULT_THRESHOLD)
    
    parser.add_argument(
        '--merge-overlaps',
        help='merge overlapping detections.',
        action=BooleanOptionalAction,
        default=nh.DEFAULT_MERGE_OVERLAPS)

    parser.add_argument(
        '--output-dir',
        help=(
            'directory in which to write output files. (default: input '
            'file directories)'),
        type=Path,
        dest='output_dir_path',
        default=nh.DEFAULT_OUTPUT_DIR_PATH)    
    
    return parser.parse_args()


def parse_hop_duration(value):
    
    try:
        hop = float(value)
    except Exception:
        handle_hop_duration_error(value)

    if hop <= 0 or hop > nh.MODEL_INPUT_DURATION:
        handle_hop_duration_error(value)
    
    return hop


def handle_hop_duration_error(value):
    raise ArgumentTypeError(
        f'Bad hop duration "{value}". Hop duration must be '
        f'a number in the range (0, {nh.MODEL_INPUT_DURATION}].')    


def parse_threshold(value):
    
    try:
        threshold = float(value)
    except Exception:
        handle_threshold_error(value)
    
    if threshold < 0 or threshold > 100:
        handle_threshold_error(value)
    
    return threshold
    
    
def handle_threshold_error(value):
    raise ArgumentTypeError(
        f'Bad detection threshold "{value}". Threshold must be '
        f'a number in the range [0, 100].')


def process_detections(input_file_path, output_dir_path):

    sample_rate = librosa.get_samplerate(input_file_path)
    
    # Get output directory path.
    if output_dir_path is None:
        dir_path = input_file_path.parent
    else:
        dir_path = output_dir_path

    # Get detector output CSV and Vesper JSON detection file paths.
    stem = f'{input_file_path.stem}_detections'
    csv_file_path = dir_path / f'{stem}.csv'
    json_file_path = dir_path / f'{stem}.json'

    with open(csv_file_path, 'r', newline='') as csv_file, \
            open(json_file_path, 'w', newline='') as json_file:
       
        def write_line(line):
            json_file.write(f'        {line}\n')

        csv_reader = csv.DictReader(csv_file)

        json_file.write(JSON_FILE_HEADER)

        # The last JSON line for the previous detection. We keep track
        # of this so we can add a comma to the last JSON line for every
        # detection except the last.
        last_json_line = None

        for row in csv_reader:

            if last_json_line is not None:
                # this is not the first detection

                # Output the last JSON line for the previous detection,
                # including a trailing comma.
                write_line(last_json_line + ',')

            json_text = get_detection_json(row, sample_rate)

            # Output all JSON lines for this detection except for the last.
            json_lines = json_text.split('\n')
            for line in json_lines[:-1]:
                write_line(line)

            # Save the last JSON line for this detection.
            last_json_line = json_lines[-1]

        # If there were any detections, output the last JSON line for
        # the last detection with no trailing comma.
        if last_json_line is not None:
            write_line(last_json_line)

        json_file.write(JSON_FILE_TRAILER)


def get_detection_json(row, sample_rate):

    def time_to_index(time):
        return int(round(time * sample_rate))

    start_index = time_to_index(float(row['start_sec']))
    end_index = time_to_index(float(row['end_sec']))

    annotations = OrderedDict((
        ('Detector Score', row['prob']),
        ('Classification', row['class']),
        ('Classifier Score', row['prob']),
        ('Nighthawk Class', row['class']),
        ('Nighthawk Class Probability', row['prob']),
        ('Nighthawk Order', row['order']),
        ('Nighthawk Order Probability', row['prob_order']),
        ('Nighthawk Family', row['family']),
        ('Nighthawk Family Probability', row['prob_family']),
        ('Nighthawk Group', row['group']),
        ('Nighthawk Group Probability', row['prob_group']),
        ('Nighthawk Species', row['species']),
        ('Nighthawk Species Probability', row['prob_species'])
    ))

    output_detection = OrderedDict((
        ('start_index', start_index),
        ('end_index', end_index),
        ('annotations', annotations)
    ))

    return json.dumps(output_detection, indent=4)


if __name__ == '__main__':
    main()
