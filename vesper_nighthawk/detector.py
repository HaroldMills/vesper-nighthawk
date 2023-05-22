"""Vesper detector provider plugin for Nighthawk NFC detector."""


from collections import OrderedDict
from contextlib import AbstractContextManager
from pathlib import Path
import csv
import json
import logging
import tempfile
import wave

import numpy as np

import vesper_nighthawk.conda_utils as conda_utils


# TODO: Deliver log messages to listener rather than logging them directly.
# TODO: Consider putting `conda_utils` into its own Python package.
# TODO: Consider using `pluggy` Python plugin framework.
# TODO: Allow support for different detector versions from one detector
#       series to be provided by different detector providers.
# TODO: Modify Vesper detection infrastructure to automatically generate
#       detector setting UI from metadata from detector provider.


_SUPPORTED_DETECTOR_SERIES_NAMES = ('Nighthawk',)


def _parse_hop_size(value):
    
    try:
        hop = float(value)
    except Exception:
        _handle_hop_size_error(value)

    if hop <= 0 or hop > 100:
        _handle_hop_size_error(value)
    
    return hop


def _handle_hop_size_error(value):
    raise _SettingError(
        f'Bad hop size "{value}". Hop size must be a number in the '
        f'range (0, 100].')


_NIGHTHAWK_SETTING_INFO = {
    'hs': {'name': 'hop_size', 'value_parser': _parse_hop_size},
    'mo': {'name': 'merge_overlaps', 'value': True},
    'nmo': {'name': 'merge_overlaps', 'value': False},
    'du': {'name': 'drop_uncertain', 'value': True},
    'ndu': {'name': 'drop_uncertain', 'value': False},
}

_SPECIES_CODE_TYPE_EBIRD = 'ebird'
_SPECIES_CODE_TYPE_IBP = 'ibp'
_SPECIES_CODE_TYPES = frozenset((
    _SPECIES_CODE_TYPE_EBIRD, _SPECIES_CODE_TYPE_IBP
))
_DATA_DIR_PATH = Path(__file__).parent / 'data'
_SPECIES_CODE_MAPPING_FILE_PATH = _DATA_DIR_PATH / 'species_code_mapping.json'


'''
Examples of detector names in Vesper:
    Nighthawk 0.1.0 80
    Nighthawk 0.1.0 90
    Nighthawk 0.1.0 90 ibp
    Nighthawk 0.1.0 90 hs 20.1
    Nighthawk 0.1.0 90 hs 20.1 nmo du

Detector class name for last example: Nighthawk_0x1x0_90_hs_20x1_nmo_du
'''


def get_supported_detector_series_names():

    """
    Gets the names of the detector series supported by this plugin.

    For the time being, we rather naively assume that if a plugin supports
    one detector version in a detector series it supports all versions in
    the series. A later version of the detector provider plugin interface
    will support more flexible descriptions of supported detectors.
    """

    return frozenset(_SUPPORTED_DETECTOR_SERIES_NAMES)


def parse_detector_settings(series_name, version_number, settings):

    """
    Parses detector settings.

    The settings are returned in a dictionary that maps setting name
    to setting value.

    For the time being, the detector provider plugin interface works
    with detector names of the form:

        <series name> <version number> <settings>

    where <series name> is the detector series name, e.g. "Nighthawk",
    <version number> is a detector version number, e.g. "1.0.0", and
    <settings> is a space-delimited list of detector setting values.
    The Vesper detection infrastructure parses a detector name into a
    series name, a version number, and a list of detector settings,
    and delegates parsing of the settings to this function.

    A later version of the detector provider plugin interface will
    allow a detector provider to provide metadata describing the
    names and types of detector settings, which Vesper will use to
    automatically generate detector setting user interfaces.
    """

    setting_count = len(settings)

    if setting_count == 0:
        raise _SettingError('No threshold specified.')
    
    threshold = _parse_threshold(settings[0])
    result = {'threshold': threshold}

    i = 1

    while i != setting_count:

        code = settings[i]

        if code in _SPECIES_CODE_TYPES:
            result['species_code_type'] = code
            i += 1

        else:

            info = _NIGHTHAWK_SETTING_INFO.get(code)

            if info is None:
                raise _SettingError(
                    f'Unrecognized detector setting name "{code}".')
            
            name = info['name']
            
            value_parser = info.get('value_parser')

            if value_parser is None:
                # setting value fixed

                result[name] = info['value']
                i += 1

            else:
                # setting value not fixed

                if i == setting_count - 1:
                    raise _SettingError(
                        f'No setting value after name "{code}" that '
                        f'requires one.')
                
                value = value_parser(settings[i + 1])
                result[name] = value
                i += 2

    return result


def _parse_threshold(value):
    
    try:
        threshold = float(value)
    except Exception:
        _handle_threshold_error(value)
    
    if threshold < 0 or threshold > 100:
        _handle_threshold_error(value)
    
    return threshold
    
    
def _handle_threshold_error(value):
    raise _SettingError(
        f'Bad threshold "{value}". Threshold must be a number in the '
        f'range [0, 100].')


def get_detector_class(extension_name, series_name, version_number, settings):

    """
    Get a detector class for the specified detector series, version,
    and detector settings. The Vesper detection infrastructure invokes
    this function to get a detector class that it can instantiate and
    use to perform detection.
    """
    
    class_dict = {
        'extension_name': extension_name,
        'series_name': series_name,
        'version_number': version_number,
        '_settings': settings
    }
    
    class_name = _get_class_name(series_name, version_number, settings)

    return type(class_name, (_Detector,), class_dict)


def _get_class_name(series_name, version_number, settings):

    threshold = _format_number(settings.get('threshold'))
    hop_size = _format_number(settings.get('hop_size'), 'hs')
    merge_overlaps = _format_boolean(settings.get('merge_overlaps'), 'mo')
    drop_uncertain = _format_boolean(settings.get('drop_uncertain'), 'du')
    species_code_type = _format_enum(settings.get('species_code_type'))

    return (
        f'{series_name}_{version_number}{threshold}{hop_size}'
        f'{merge_overlaps}{drop_uncertain}'
        f'{species_code_type}').replace('.', 'x')


def _format_number(x, code=None):
    if x is None:
        return ''
    elif code is None:
        return f'_{x}'
    else:
        return f'_{code}_{x}'
    

def _format_boolean(x, code):
    if x is None:
        return ''
    elif x:
        return f'_{code}'
    else:
        return f'_n{code}'


def _format_enum(x):
    if x is None:
        return ''
    else:
        return f'_{x}'
    

class _Detector:
    
    """
    Vesper wrapper for Nighthawk NFC detector.
    
    An instance of this class wraps Nighthawk as a Vesper detector.
    The instance operates on a single audio channel. It accepts a sequence
    of consecutive sample arrays of any sizes via its `detect` method,
    concatenates them in a temporary audio file, and runs Nighthawk
    on the audio file when its `complete_detection` method is called.
    Nighthawk is run in its own Conda environment, which can be
    different from the Conda environment in which the Vesper server is
    running. After Nighthawk finishes processing the file,
    `complete_detection` invokes a listener's `process_clip` method for
    each of the resulting clips. The `process_clip` method must accept
    three arguments: the start index and length of the detected clip,
    and a dictionary of annotations for the clip.
    """
    
    
    def __init__(self, input_sample_rate, listener):
        
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        # Create and open temporary detector input audio file.
        # Do not delete automatically on close. We will close the
        # file after we finish writing it, and then Nighthawk will
        # open it again for reading. We delete the file ourselves
        # after Nighthawk finishes processing it.
        self._input_file = tempfile.NamedTemporaryFile(
            suffix='.wav', delete=False)
        
        # Create detector input audio file writer.
        self._input_file_writer = _WaveFileWriter(
            self._input_file, 1, self._input_sample_rate)
        
        self._taxon_mapping = self._get_taxon_mapping()
        

    def _get_taxon_mapping(self):

        species_code_type = self.settings.get('species_code_type')

        if species_code_type == _SPECIES_CODE_TYPE_IBP:
            with open(_SPECIES_CODE_MAPPING_FILE_PATH) as file:
                return json.load(file)
            
        else:
            return {}
        

    @property
    def settings(self):
        return self._settings
    
    
    @property
    def input_sample_rate(self):
        return self._input_sample_rate
    
    
    @property
    def listener(self):
        return self._listener
    
    
    def detect(self, samples):
        self._input_file_writer.write(samples)
    
    
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        # Close input file writer and input file.
        self._input_file_writer.close()
        self._input_file.close()
        
        input_file_path = Path(self._input_file.name)
        
        with tempfile.TemporaryDirectory() as output_dir_path, \
                _FileDeleter(input_file_path):
            
            output_dir_path = Path(output_dir_path)
            
            module_name = 'nighthawk.run_nighthawk'
            
            # Build list of command line arguments.
            args = self._get_command_args(input_file_path, output_dir_path)
            
            environment_name = f'nighthawk-{self.version_number}'
            
            try:
                results = conda_utils.run_python_script(
                    module_name, args, environment_name)
            
            except Exception as e:
                raise _DetectorError(
                    f'Could not run {self.extension_name} in Conda '
                    f'environment "{environment_name}". Error message '
                    f'was: {e}')
            
            self._log_detector_results(results)
            
            if results.returncode != 0:
                # detector process completed abnormally
                
                raise _DetectorError(
                    f'{self.extension_name} process completed abnormally. '
                    f'See above log messages for details.')
            
            else:
                # detector process completed normally
                
                detection_file_path = self._get_detection_file_path(
                    input_file_path, output_dir_path)
                self._process_detection_file(detection_file_path)
    
    
    def _get_command_args(self, input_file_path, output_dir_path):

        settings = self.settings

        args = []

        hop_size = settings.get('hop_size')
        if hop_size is not None:
            args += ['--hop-size', str(hop_size)]

        threshold = settings.get('threshold')
        if threshold is not None:
            args += ['--threshold', str(threshold)]

        merge_overlaps = settings.get('merge_overlaps')
        if merge_overlaps is not None:
            prefix = '' if merge_overlaps else 'no-'
            args.append('--' + prefix + 'merge-overlaps')

        drop_uncertain = settings.get('drop_uncertain')
        if drop_uncertain is not None:
            prefix = '' if drop_uncertain else 'no-'
            args.append('--' + prefix + 'drop-uncertain')

        args += ['--output-dir', str(output_dir_path)]

        args.append(str(input_file_path))

        return args


    def _log_detector_results(self, results):
        
        if results.returncode != 0:
            # detector process completed abnormally.
            
            logging.info(
                f'        {self.extension_name} process completed '
                f'abnormally with return code {results.returncode}. '
                f'No clips will be created.')
        
        else:
            # detector process completed normally
            
            logging.info(
                f'        {self.extension_name} process completed normally.')
        
        self._log_process_output_stream(results.stdout, 'standard output')
        self._log_process_output_stream(results.stderr, 'standard error')
    
    
    def _log_process_output_stream(self, stream_text, stream_name):
        
        if len(stream_text) == 0:
            
            logging.info(
                f'        {self.extension_name} process {stream_name} '
                f'was empty.')
        
        else:
            
            logging.info(
                f'        {self.extension_name} process {stream_name} was:')
            
            lines = stream_text.strip().splitlines()
            for line in lines:
                logging.info(f'            {line}')
    
    
    def _get_detection_file_path(self, input_file_path, output_dir_path):
        detection_file_name = f'{input_file_path.stem}_detections.csv'
        return output_dir_path / detection_file_name
    
    
    def _process_detection_file(self, file_path):
        
        start_indices = set()

        with open(file_path, newline='') as csv_file, \
                open(file_path, newline='') as text_file:
            
            reader = csv.DictReader(csv_file)

            # Skip header.
            text_file.readline()
            
            for row in reader:

                # Get file line from which `row` was created.
                line = text_file.readline().strip()

                try:
                    start_index, length, annotations = self._get_clip(
                        row, self._input_sample_rate, start_indices, line)
                    
                except Exception as e:
                    logging.warning(f'{e}. Clip will be ignored.')

                else:
                    self._listener.process_clip(
                        start_index, length, annotations=annotations)
        
        self._listener.complete_processing()


    def _get_clip(self, row, sample_rate, start_indices, line):

        unincremented_start_index = \
            _time_to_index(float(row['start_sec']), sample_rate)

        start_index = _make_start_index_unique(
            unincremented_start_index, start_indices)

        # We never increment the end index of a clip, even if we increment
        # the start index, since that could push the end index past the end
        # of the input. So incrementing the start index shortens a clip.
        end_index = _time_to_index(float(row['end_sec']), sample_rate)

        # It would be extremely surprising if incrementing the start index
        # moved it past the end index, since a clip usually has thousands
        # of samples, but we check for that anyway, just to be sure.
        if start_index > end_index:
            start_time = row['start_sec']
            raise _DetectorError(
                f'For clip starting {start_time} seconds into recording '
                f'file, incrementing start index to make it unique moved '
                f'it past end index.')
        
        length = end_index - start_index

        species = self._map_taxon(row['species'])
        predicted_category = self._map_taxon(row['predicted_category'])

        classification = 'Call.' + predicted_category
        score = str(100 * float(row['prob']))

        annotations = OrderedDict((
            ('Detector Score', score),
            ('Classification', classification),
            ('Classifier Score', score),
            ('Nighthawk Order', row['order']),
            ('Nighthawk Order Probability', row['prob_order']),
            ('Nighthawk Family', row['family']),
            ('Nighthawk Family Probability', row['prob_family']),
            ('Nighthawk Group', row['group']),
            ('Nighthawk Group Probability', row['prob_group']),
            ('Nighthawk Species', species),
            ('Nighthawk Species Probability', row['prob_species']),
            ('Nighthawk Predicted Category', predicted_category),
            ('Nighthawk Probability', row['prob']),
            ('Nighthawk Output File Line', line),
        ))

        if start_index != unincremented_start_index:
            # start index was incremented

            offset = start_index - unincremented_start_index
            annotations['Start Index Uniqueness Offset'] = str(offset)

        return start_index, length, annotations
    

    def _map_taxon(self, taxon):
        return self._taxon_mapping.get(taxon, taxon)


def _time_to_index(time, sample_rate):
    return int(round(time * sample_rate))
    

def _make_start_index_unique(start_index, start_indices):

    """Increments the specified start index as needed to make it unique."""

    while start_index in start_indices:
        start_index += 1

    start_indices.add(start_index)

    return start_index

    
class _SettingError(Exception):
    pass


class _DetectorError(Exception):
    pass


class _FileDeleter(AbstractContextManager):
    
    def __init__(self, file_path):
        self._file_path = file_path
    
    def __exit__(self, exception_type, exception_value, traceback):
        self._file_path.unlink(missing_ok=True)


class _WaveFileWriter:
    
    """Writes a .wav file one sample array at a time."""
    
    
    def __init__(self, file_, num_channels, sample_rate):
        self._writer = wave.open(file_, 'wb')
        self._writer.setparams((num_channels, 2, sample_rate, 0, 'NONE', None))
    
    
    def write(self, samples):
        
        # Convert samples to wave file dtype if needed.
        if samples.dtype != np.dtype('<i2'):
            samples = np.array(np.round(samples), dtype='<i2')
        
        # Convert samples to bytes.
        data = samples.transpose().tobytes()
        
        self._writer.writeframes(data)
    
    
    def close(self):
        self._writer.close()
