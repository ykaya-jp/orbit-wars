.PHONY: help install download play episodes replay logs lb submit submit-tar lint test fmt clean

SLUG := orbit-wars
PKG  := orbit_wars
UV   := uv
AGENT := src/$(PKG)/agent.py

help:
	@echo "Targets (RL/agent comp):"
	@echo "  install      - uv sync (install deps incl. kagglib editable + kaggle-environments)"
	@echo "  download     - kaggle competitions download -c $(SLUG) -p data/raw + unzip"
	@echo "  play         - run local episode: agent vs random (configurable)"
	@echo "  play-self    - agent vs agent (sanity check on symmetry)"
	@echo "  submit       - kaggle competitions submit -f $(AGENT) -m '...' (single-file agent)"
	@echo "  submit-tar   - bundle src/$(PKG)/ as submission.tar.gz then submit (multi-file)"
	@echo "  submissions  - list past submissions"
	@echo "  episodes     - list episodes for SUB_ID=<id>"
	@echo "  replay       - download replay JSON for EP_ID=<id>"
	@echo "  logs         - download agent logs for EP_ID=<id> AGENT_IDX=<0|1>"
	@echo "  lb           - show leaderboard"
	@echo "  lint/test/fmt/clean — standard"

install:
	$(UV) sync --extra dev
	$(UV) run pre-commit install >/dev/null 2>&1 || true

download:
	$(UV) run kaggle competitions download -c $(SLUG) -p data/raw
	@cd data/raw && for z in *.zip; do [ -f "$$z" ] && unzip -o -q "$$z" && rm "$$z" || true; done
	@echo "downloaded to data/raw/"
	@ls -la data/raw

play:
	$(UV) run python -m $(PKG).play

play-self:
	$(UV) run python -m $(PKG).play --opponent self

submit:
	@if [ -z "$(M)" ]; then echo "usage: make submit M='your message'"; exit 1; fi
	@mkdir -p submissions
	@SHA=$$(git rev-parse --short HEAD); \
	  cp $(AGENT) submissions/main.py; \
	  cp $(AGENT) submissions/main_$${SHA}.py; \
	  $(UV) run kaggle competitions submit $(SLUG) -f submissions/main.py -m "$${SHA} $(M)"; \
	  git tag exp_$${SHA}_$$(echo "$(M)" | tr ' ' '_' | head -c 60) || true

# Multi-file agent: bundle the whole package + any model weights
SUBMIT_TAR := submissions/submission.tar.gz
submit-tar:
	@if [ -z "$(M)" ]; then echo "usage: make submit-tar M='your message'"; exit 1; fi
	mkdir -p submissions
	@# Pack: rename src/PKG/agent.py -> top-level main.py, include the rest as helpers
	tar -czf $(SUBMIT_TAR) \
		--transform 's,^src/$(PKG)/agent.py$$,main.py,' \
		--exclude='__pycache__' \
		-C . src/$(PKG)
	$(UV) run kaggle competitions submit $(SLUG) -f $(SUBMIT_TAR) -m "$$(git rev-parse --short HEAD) $(M)"
	@git tag exp_$$(git rev-parse --short HEAD)_$$(echo "$(M)" | tr ' ' '_' | head -c 60) || true

submissions:
	$(UV) run kaggle competitions submissions $(SLUG)

episodes:
	@if [ -z "$(SUB_ID)" ]; then echo "usage: make episodes SUB_ID=<submission-id>"; exit 1; fi
	$(UV) run kaggle competitions episodes $(SUB_ID)

replay:
	@if [ -z "$(EP_ID)" ]; then echo "usage: make replay EP_ID=<episode-id>"; exit 1; fi
	mkdir -p outputs/replays
	$(UV) run kaggle competitions replay $(EP_ID) -p outputs/replays
	@echo "saved to outputs/replays/"

logs:
	@if [ -z "$(EP_ID)" ] || [ -z "$(AGENT_IDX)" ]; then echo "usage: make logs EP_ID=<episode-id> AGENT_IDX=<0|1>"; exit 1; fi
	mkdir -p outputs/logs
	$(UV) run kaggle competitions logs $(EP_ID) $(AGENT_IDX) -p outputs/logs

lb:
	$(UV) run kaggle competitions leaderboard $(SLUG) -s

lint:
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests

fmt:
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

test:
	$(UV) run pytest tests -q

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf outputs/replays/* outputs/logs/*
	@touch outputs/logs/.gitkeep
