.PHONY: init preflight test cli-smoke package-smoke validate resolve resolve-example

RUNTIME ?= codex

init:
	PYTHONPATH=src python3 tools/init_agentcaravan.py --runtime "$(RUNTIME)"

preflight:
	PYTHONPATH=src python3 -m agentcaravan.scripts manifest
	PYTHONPATH=src python3 -m agentcaravan.scripts compile

test:
	PYTHONPATH=src python3 -m agentcaravan.scripts tests

cli-smoke:
	PYTHONPATH=src python3 -m agentcaravan.scripts cli-smoke

package-smoke:
	PYTHONPATH=src python3 -m agentcaravan.scripts package-smoke

validate:
	PYTHONPATH=src python3 -m agentcaravan.scripts validate

resolve:
	PYTHONPATH=src python3 -m agentcaravan.scripts resolve

resolve-example:
	PYTHONPATH=src python3 -m agentcaravan.scripts resolve-example
