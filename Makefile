.PHONY: run test doctor clean deb

run:
	./bin/unzzz serve --data-dir ./data --bind 0.0.0.0 --port 8888

test:
	python3 -m unittest discover -s tests -v

doctor:
	./bin/unzzz doctor --data-dir ./data

deb:
	./packaging/build-deb.sh

clean:
	rm -rf data tmpdata build .tooling .npm-cache .playwright-browsers .chrome-home .chrome-profile
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
