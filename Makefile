PYTHON ?= python3
CREDITS ?= 500

.PHONY: preflight test ledger-set-balance sarvam-selftest activate-sarvam export

preflight:
	$(PYTHON) scripts/preflight.py

test:
	$(PYTHON) tests/test_stage1_unit.py
	$(PYTHON) tests/test_e2e_stage1.py
	$(PYTHON) tests/test_stage2.py
	$(PYTHON) tests/qa_battery.py

ledger-set-balance:
	$(PYTHON) scripts/sarvam_cli.py set-balance --credits $(CREDITS)

sarvam-selftest:
	$(PYTHON) scripts/sarvam_cli.py selftest

activate-sarvam:
	$(PYTHON) scripts/sarvam_cli.py activate

export:
	mkdir -p exports
	git bundle create exports/paytmai-vyaparvoice.bundle --all
	@echo "Exported git bundle to exports/paytmai-vyaparvoice.bundle"
