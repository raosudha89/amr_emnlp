import sys, os
import re
import networkx as nx
import pyparsing
import cPickle as pickle

def main(argv):
	if len(argv) < 1:
		print "usage: remove_proxy_test_sets.py <amr_input_file> <amr_output_file>"
		return
	amr_input_file = open(argv[0], 'r')
	amr_output_file = open(argv[1], 'w')
	line = amr_input_file.readline()
	stop_writing = False
	while (line != ""):
		if line.rstrip("\n") == "":
			amr_output_file.write(line)
			line = amr_input_file.readline()
			continue
		if line.startswith("# ::id"):
			if 'PROXY' in line:
				stop_writing = True
			else:
				stop_writing = False
		if not stop_writing:
			amr_output_file.write(line)
		line = amr_input_file.readline()

if __name__ == "__main__":
    main(sys.argv[1:])
