import sys

def main(argv):
	if len(argv) < 2:
		print "usage: extract_sentences_from_amr_input.py <amr_file> <out_file>"
		return
	amr_aligned = open(argv[0])
	out_file = open(argv[1], 'w')
	line = amr_aligned.readline()
	while (line != ""):
		if line.startswith("# ::tok"):
			out_file.write(line.strip("# ::tok"))
		if line.startswith("# ::snt"):
			out_file.write(line.strip("# ::snt"))
		line = amr_aligned.readline()
	
if __name__ == "__main__":
	main(sys.argv[1:])
