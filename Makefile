.PHONY: regen-types install test

regen-types:
	datamodel-codegen \
		--input src/compassql/schemas/vega-lite-v5.json \
		--input-file-type jsonschema \
		--output src/compassql/vegalite_types.py \
		--enum-field-as-literal one \
		--use-standard-collections

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short
