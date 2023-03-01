"""
Module containing vesper-nighthawk version.

This module is the authority regarding the vesper-nighthawk version. Any
other module that needs the vesper-nighthawk version should obtain it from
this module.
"""


major_number = 0
minor_number = 0
patch_number = 0
suffix = ''

major_version = f'{major_number}'
minor_version = f'{major_version}.{minor_number}'
patch_version = f'{minor_version}.{patch_number}'
full_version = f'{patch_version}{suffix}'
