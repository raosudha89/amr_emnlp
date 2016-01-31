import sys, os
import re
import cPickle as pickle


def main(argv):
	if len(argv) < 1:
		print "usage: amr_reader.py <amr_file>"
		return
	amr_aligned = open(argv[0])
	ids = []
	sentences = []
	line = amr_aligned.readline()
	while (line != ""):
		if line.startswith("# ::id"):
			ids.append(line.split("::")[1].strip("# ::id").strip())
		if line.startswith("# ::snt"):
			sentences.append(line.strip("# ::snt").strip("\n"))
		line = amr_aligned.readline()

	amr_nx_graphs = {}
	print_to_file = 1
	for i in range(len(ids)):
		amr_nx_graphs[ids[i]] = [sentences[i]]
	pickle.dump(amr_nx_graphs, open("amr_nx_graphs.p", "wb"))

if __name__ == "__main__":
    main(sys.argv[1:])
