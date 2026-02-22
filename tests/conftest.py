from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent / 'test_data'
VALID_SCHEMA = TEST_DATA_DIR / 'valid_sdc4_schema.xsd'
INVALID_SCHEMA = TEST_DATA_DIR / 'invalid_sdc4_schema_with_extension.xsd'
NON_SDC4_SCHEMA = TEST_DATA_DIR / 'non_sdc4_schema_with_extension.xsd'
SDC4_EXAMPLE_SCHEMA = TEST_DATA_DIR / 'dm-jsi5yxnvzsmsisgn2bvelkni.xsd'
