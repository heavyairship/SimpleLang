# FixMe: organize this repo properly with setup.py, etc.
# FixMe: add README.md

PYTHON = /usr/bin/python3

clean:
	rm -rf __pycache__ *.pyc simple_lang/__pycache__ simple_lang/*pc build/ dist/ simple_lang.egg-info

install:
	pip3 install . --user
	cp simple_lang/simple_lang.py /usr/local/bin/simple_lang.py

check: clean install
	echo "\nrunning test.py" && $(PYTHON) tests/test.py && \
	echo "\nrunning test.sl" && $(PYTHON) simple_lang.py examples/test.sl --verbose && \
	echo "\nrunning factorial.sl" && $(PYTHON) simple_lang.py examples/factorial.sl --verbose && \
	echo "\nrunning log_2.sl" && $(PYTHON) simple_lang.py examples/log_2.sl --verbose && \
	echo "\nrunning higher_order.sl" && $(PYTHON) simple_lang.py examples/higher_order.sl --verbose && \
	echo "\nrunning factorial_rec.sl" && $(PYTHON) simple_lang.py examples/factorial_rec.sl --verbose && \
	echo "\nrunning call_test.sl" && $(PYTHON) simple_lang.py examples/call_test.sl --verbose && \
	echo "\nrunning list_example.sl" && $(PYTHON) simple_lang.py examples/list_example.sl --verbose 

