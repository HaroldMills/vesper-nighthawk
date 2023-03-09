import pytest

from vesper_nighthawk.detector import _SettingError
import vesper_nighthawk.detector as detector


@pytest.mark.parametrize('settings, expected_result', [

    ('50', {'threshold': 50}),
    ('90.25', {'threshold': 90.25}),
    ('90 25', {'threshold': 90, 'hop_size': 25}),
    ('90 MO', {'threshold': 90, 'merge_overlaps': True}),
    ('90 NMO', {'threshold': 90, 'merge_overlaps': False}),
    ('90 DU', {'threshold': 90, 'drop_uncertain': True}),
    ('90 NDU', {'threshold': 90, 'drop_uncertain': False}),
    ('90 MO DU',
         {'threshold': 90, 'merge_overlaps': True, 'drop_uncertain': True}),
    ('90 25 MO',
         {'threshold': 90, 'hop_size': 25, 'merge_overlaps': True}),

    # These might be considered errors, but they aren't for now.
    ('90 MO MO', {'threshold': 90, 'merge_overlaps': True}),
    ('90 MO NMO', {'threshold': 90, 'merge_overlaps': False}),

])
def test_parse_detector_settings(settings, expected_result):
    settings = settings.split()
    result = detector.parse_detector_settings('Nighthawk', '0.0.0', settings)
    assert result == expected_result


@pytest.mark.parametrize('settings, expected_message', [
    ('Bobo', (
        'Bad threshold "Bobo". Threshold must be a number in the range '
        '[0, 100].')),
    ('-1', (
        'Bad threshold "-1". Threshold must be a number in the range '
        '[0, 100].')),
    ('101', (
        'Bad threshold "101". Threshold must be a number in the range '
        '[0, 100].')),
    ('90 0', (
        'Bad hop size "0". Hop size must be a number in the range '
        '(0, 100].')),
    ('90 101', (
        'Bad hop size "101". Hop size must be a number in the range '
        '(0, 100].')),
    ('90 Bobo', 'Unrecognized detector setting value "Bobo".'),
    ('90 MO 25', (
        'Hop size "25" specified out of place. Hop size must '
        'immediately follow threshold.')),
])
def test_parse_detector_settings_errors(settings, expected_message):
    settings = settings.split()
    with pytest.raises(_SettingError) as exc_info:
        detector.parse_detector_settings('Nighthawk', '0.0.0', settings)
    message = str(exc_info.value)
    assert message == expected_message
