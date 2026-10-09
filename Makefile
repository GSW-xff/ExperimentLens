.PHONY: verify start demo benchmark evaluation

verify:
	./scripts/verify.sh

start:
	./scripts/start_local.sh

demo:
	./scripts/interview_demo.sh

benchmark:
	experimentlens-benchmark --runs 100 --workers 2

evaluation:
	experimentlens-eval
