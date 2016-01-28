import sys, os
from xml.dom import minidom
import cPickle as pickle

def main(argv):
	vnpbMappings_xml_file = open(argv[0])
	output_dir = argv[1]
	xmldoc = minidom.parse(vnpbMappings_xml_file)
	predicateList = xmldoc.getElementsByTagName('predicate')
	words_concepts = {}	
	for predicate in predicateList:
		verb = predicate.attributes['lemma'].value
		if not words_concepts.has_key(verb):
			words_concepts[verb] = []
		argmapList = predicate.getElementsByTagName('argmap')
		for argmap in argmapList:
			verb_sense = argmap.attributes['pb-roleset'].value
			concept = "-".join(verb_sense.split("."))
			if concept not in words_concepts[verb]:
				words_concepts[verb].append(str(concept))
	print_to_file = 1
	if print_to_file:
		for key, value in words_concepts.items():
			print key, value
	pickle.dump(words_concepts, open(os.path.join(output_dir, "vnpb_words_concepts_dict.p"), "wb"))

if __name__ == "__main__":
	main(sys.argv[1:])
