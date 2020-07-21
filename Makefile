# FixMe: organize this repo properly with setup.py, etc.
# FixMe: add README.md

PYTHON = /usr/bin/python3

check:
	$(PYTHON) test.py && \
	$(PYTHON) simple_lang.py --file test.sl --verbose && \
	$(PYTHON) simple_lang.py --file factorial.sl --verbose && \
	$(PYTHON) simple_lang.py --file log_2.sl --verbose

clean:
	rm -rf __pycache__ *.pyc