# Makefile variables set automatically
plugin_id=`cat plugin.json | python3 -c "import sys, json; print(str(json.load(sys.stdin)['id']).replace('/',''))"`
plugin_version=`cat plugin.json | python3 -c "import sys, json; print(str(json.load(sys.stdin)['version']).replace('/',''))"`
archive_file_name="dss-plugin-${plugin_id}-${plugin_version}.zip"


plugin:
	@echo "[START] Archiving plugin to dist/ folder..."
	@python3 -c 'import json; json.load(open("plugin.json"))'
	@rm -rf dist
	@mkdir dist
	@REMOTE_URL="$$(git config --get remote.origin.url 2>/dev/null || true)" LAST_COMMIT_ID="$$(git rev-parse HEAD 2>/dev/null || true)" python3 -c 'import json, os; json.dump({"remote_url": os.environ.get("REMOTE_URL") or None, "last_commit_id": os.environ.get("LAST_COMMIT_ID") or None}, open("release_info.json", "w"))'
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		git archive -v -9 --format zip -o dist/${archive_file_name} HEAD; \
		zip --delete dist/${archive_file_name} "tests/*"; \
	else \
		zip -rq dist/${archive_file_name} . \
			-x "tests/*" \
			-x "env/*" \
			-x "dist/*" \
			-x ".git/*" \
			-x ".pytest_cache/*" \
			-x "release_info.json" \
			-x "__pycache__/*" \
			-x "*/__pycache__/*" \
			-x "*.pyc" \
			-x "*.DS_Store"; \
	fi
	@zip -u dist/${archive_file_name} release_info.json
	@rm release_info.json
	@echo "[SUCCESS] Archiving plugin to dist/ folder: Done!"

unit-tests:
	@echo "Running unit tests..."
	@( \
		rm -rf ./env/; \
		python3 -m venv env/; \
		source env/bin/activate; \
		pip install --upgrade pip;\
		pip install --no-cache-dir -r tests/python/unit/requirements.txt; \
		export PYTHONPATH="$(PYTHONPATH):$(PWD)/python-lib"; \
		pytest tests/python/unit --alluredir=tests/allure_report || ret=$$?; exit $$ret \
	)

tests: unit-tests

dist-clean:
	rm -rf dist
