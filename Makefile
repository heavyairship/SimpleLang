# FixMe: add full README.md

PYTHON = /usr/bin/python3

clean:
	rm -rf __pycache__ *.pyc swimlang/__pycache__ swimlang/*.pyc build/ dist/ swimlang.egg-info

install:
	pip3 install . --user
	cp ./swimlang/swim.py /usr/local/bin/swim
	cp ./swimlang/swimfmt.py /usr/local/bin/swimfmt

uninstall:
	pip3 uninstall -y swimlang
	rm -f /usr/local/bin/swim
	rm -f /usr/local/bin/swimfmt

lint:
	swimfmt examples/log_2.sl && \
	swimfmt examples/call_test.sl && \
	swimfmt examples/factorial.sl && \
	swimfmt examples/factorial_rec.sl && \
	swimfmt examples/higher_order.sl && \
	swimfmt examples/list_example.sl && \
	swimfmt examples/test.sl && \
	swimfmt examples/bst.sl && \
	swimfmt examples/maps.sl && \
	swimfmt examples/map_reduce.sl && \
	swimfmt examples/fizz_buzz.sl && \
	swimfmt examples/print_primes.sl && \
	swimfmt examples/boomerang.sl && \
	swimfmt examples/gcd_lcm.sl && \
	swimfmt examples/nested_len.sl && \
	swimfmt examples/type_ex.sl && \
	swimfmt examples/choose.sl && \
	swimfmt examples/distance_to_vowel.sl && \
	swimfmt examples/list_concat.sl && \
	swimfmt examples/prod_of_digit.sl && \
	swimfmt examples/hanoi.sl && \
	swimfmt examples/fibstr.sl && \
	swimfmt examples/times_table.sl

check: clean uninstall install
	#$(MAKE) lint
	(echo "\nrunning test.py" && $(PYTHON) tests/test.py && \
	echo "\nrunning test.sl" && swim examples/test.sl --verbose && \
	echo "\nrunning factorial.sl" && swim examples/factorial.sl --verbose && \
	echo "\nrunning log_2.sl" && swim examples/log_2.sl --verbose && \
	echo "\nrunning higher_order.sl" && swim examples/higher_order.sl --verbose && \
	echo "\nrunning factorial_rec.sl" && swim examples/factorial_rec.sl --verbose && \
	echo "\nrunning call_test.sl" && swim examples/call_test.sl --verbose && \
	echo "\nrunning list_example.sl" && swim examples/list_example.sl --verbose && \
	echo "\nrunning maps.sl" && swim examples/maps.sl --verbose && \
	echo "\nrunning fizz_buzz.sl" && swim examples/fizz_buzz.sl --verbose && \
	echo "\nrunning map_reduce.sl" && swim examples/map_reduce.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/bst.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/times_table.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/print_primes.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/boomerang.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/gcd_lcm.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/nested_len.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/type_ex.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/choose.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/distance_to_vowel.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/list_concat.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/prod_of_digit.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/hanoi.sl --verbose && \
	echo "\nrunning bst.sl" && swim examples/fibstr.sl --verbose && \
	echo "\ntests passed") || (echo "\ntests failed")
	
play: clean install
	swim playground.sl --verbose
