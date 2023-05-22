"""
Script that creates a JSON mapping from eBird species codes to four-letter
IBP species codes.

The script saves the mapping to the file
`vesper_nighthawk/data/species_code_mapping.json`.
"""


from collections import OrderedDict
from pathlib import Path
import json
import pandas as pd


ROOT_DIR_PATH = Path(__file__).parent.parent
SCRIPT_DIR_PATH = ROOT_DIR_PATH / 'scripts'
TAXONOMY_DIR_PATH = SCRIPT_DIR_PATH / 'data' / 'taxonomy'
EBIRD_TAXONOMY_FILE_PATH = TAXONOMY_DIR_PATH / 'ebird_taxonomy.csv'
IBP_SPECIES_FILE_PATH = TAXONOMY_DIR_PATH / 'IBP-AOS-LIST21.csv'
PACKAGE_DIR_PATH = ROOT_DIR_PATH / 'vesper_nighthawk'
MAPPING_FILE_PATH =  PACKAGE_DIR_PATH / 'data' / 'species_code_mapping.json'


def main():

    # Read input CSV files.
    ebird_df = pd.read_csv(EBIRD_TAXONOMY_FILE_PATH)
    ibp_df = pd.read_csv(IBP_SPECIES_FILE_PATH)

    # Create mapping from eBird species code to scientific name.
    ebird_scientific_names = OrderedDict(zip(ebird_df.code, ebird_df.sci_name))

    # Create mapping from scientific name to IBP species code.
    ibp_species_codes = dict(zip(ibp_df.SCINAME, ibp_df.SPEC))

    # Compose mappings, maintaining order of keys.
    mapping = OrderedDict()
    for ebird_species_code in ebird_scientific_names.keys():
        scientific_name = ebird_scientific_names[ebird_species_code]
        ibp_species_code = ibp_species_codes.get(scientific_name)
        if ibp_species_code is not None:
            mapping[ebird_species_code] = ibp_species_code

    # Write output JSON file.
    with open(MAPPING_FILE_PATH, 'wt') as file:
        json.dump(mapping, file, indent=4)


if __name__ == '__main__':
    main()
