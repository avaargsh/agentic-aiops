.PHONY: stack-lock-check acceptance-build acceptance acceptance-clean

stack-lock-check:
	PYTHONPATH=src python -m agentic_aiops.stack_lock stack.lock.json

acceptance-build: stack-lock-check
	docker build -t agent-control-plane:acceptance ../agent-control-plane
	docker build -t agent-decision-lab:acceptance ../agent-decision-lab
	docker compose -f compose.golden.yml build runtime-worker

acceptance: stack-lock-check
	bash scripts/run-acceptance.sh

acceptance-clean:
	-docker compose -f compose.golden.yml --profile demo down -v
	-kubectl -n golden-demo scale deploy/load-generator --replicas=0
