.PHONY: regen-types install test

regen-types:
	datamodel-codegen \
		--input compassql/schemas/vega-lite-v5.json \
		--input-file-type jsonschema \
		--output compassql/vegalite_types.py \
		--enum-field-as-literal one \
		--use-standard-collections

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short
