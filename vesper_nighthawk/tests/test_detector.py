import pytest

from vesper_nighthawk.detector import _SettingError
import vesper_nighthawk.detector as detector


@pytest.mark.parametrize('settings, expected_result', [

    ('50', {'threshold': 50}),
    ('90.25', {'threshold': 90.25}),
    ('90 H 25.5', {'threshold': 90, 'hop_size': 25.5}),
    ('90 MO', {'threshold': 90, 'merge_overlaps': True}),
    ('90 H 25 MO', {'threshold': 90, 'hop_size': 25, 'merge_overlaps': True}),
    ('90 MO H 25', {'threshold': 90, 'hop_size': 25, 'merge_overlaps': True}),
    ('90 NMO', {'threshold': 90, 'merge_overlaps': False}),
    ('90 DU', {'threshold': 90, 'drop_uncertain': True}),
    ('90 NDU', {'threshold': 90, 'drop_uncertain': False}),
    ('90 MO DU',
         {'threshold': 90, 'merge_overlaps': True, 'drop_uncertain': True}),

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
    ('90 H 0', (
        'Bad hop size "0". Hop size must be a number in the range '
        '(0, 100].')),
    ('90 H 101', (
        'Bad hop size "101". Hop size must be a number in the range '
        '(0, 100].')),
    ('90 H', 'No setting value after name "H" that requires one.'),
    ('90 Bobo', 'Unrecognized detector setting name "Bobo".'),
])
def test_parse_detector_settings_errors(settings, expected_message):
    settings = settings.split()
    with pytest.raises(_SettingError) as exc_info:
        detector.parse_detector_settings('Nighthawk', '0.0.0', settings)
    message = str(exc_info.value)
    assert message == expected_message


@pytest.mark.parametrize('settings, expected_name', [

    ({'threshold': 50}, 'Nighthawk_0x0x0_50'),
    ({'threshold': 90, 'hop_size': 25.1}, 'Nighthawk_0x0x0_90_H_25x1'),
    ({'threshold': 50, 'merge_overlaps': True}, 'Nighthawk_0x0x0_50_MO'),
    ({'threshold': 50, 'merge_overlaps': False}, 'Nighthawk_0x0x0_50_NMO'),
    ({'threshold': 50, 'drop_uncertain': True}, 'Nighthawk_0x0x0_50_DU'),
    ({'threshold': 50, 'drop_uncertain': False}, 'Nighthawk_0x0x0_50_NDU'),
    ({'threshold': 50, 'hop_size': 25, 'merge_overlaps': True},
         'Nighthawk_0x0x0_50_H_25_MO'),

])
def test_get_class_name(settings, expected_name):
    name = detector._get_class_name('Nighthawk', '0.0.0', settings)
    assert name == expected_name
