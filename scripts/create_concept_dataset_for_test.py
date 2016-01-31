import sys
import cPickle as pickle
import networkx as nx
import string
import re

def traverse_depth_first(concept_nx_graph, parent=None):
	node_list = [] #list of pairs (concept_instance, concept_var_name) e.g. ('establish-01', 'e')
	if parent == None:
		try:
			parent = nx.topological_sort(concept_nx_graph)[0]
		except:
			#import pdb
			#pdb.set_trace()
			parent = concept_nx_graph.nodes()[0]
	node_list.append((concept_nx_graph.node[parent]['instance'], parent))
	children = []
	for child in concept_nx_graph.successors(parent):
		if concept_nx_graph.node[child]['parent'] == parent:
			children.append(child)
	if not children:
		return node_list
	ordered_children = [None]*len(children)
	order = []
	for child in children:
		order.append(concept_nx_graph.node[child]['child_num'])
	diff = max(order) + 1 - len(order)
	for child in children:
		ordered_children[concept_nx_graph.node[child]['child_num'] - diff] = child
	for child in ordered_children:
		node_list.extend(traverse_depth_first(concept_nx_graph, parent=child))
	return node_list

def create_training_data(sentence, span_concept, pos_line, ner_line):
	training_data = []
	pattern = re.findall("<(.*?)>(.*?)</(.*?)>", ner_line)
	for p in pattern:
		named_entity = p[1]
		sentence = sentence.replace(named_entity, named_entity.replace(" ", "__"))
	words = sentence.split()
	words_pos = pos_line.split()
	i = 0 #index into words
	j = 0 #index into words_pos
	while i < len(words):
		if "__" in words[i]:
			#named entity case
			span = words[i].split("__")
			pos = [words_pos[k] for k in range(j, j+len(span))]
			training_data.append([" ".join(span), " ".join(pos), "NULL", "NULL", " ".join(ner_line.split()[int(j):int(j+len(span))])])
			j += len(span)
		else:
			[word_from_pos, pos] = words_pos[j].rsplit("_", 1)
			assert(words[i] == word_from_pos)
			training_data.append([words[i], pos, "NULL", "NULL", ner_line.split()[j]])
			j += 1
		i += 1
	return training_data

def get_training_dataset(amr_nx_graphs, amr_aggregated_metadata):
	training_dataset = {}
	print "######"

	for id, value in amr_nx_graphs.iteritems():
		print id
		span_concept = {}
		[sentence] = value
		training_dataset[id] = create_training_data(sentence, span_concept, amr_aggregated_metadata[id][1], amr_aggregated_metadata[id][2])
	return training_dataset

def main(argv):
	if len(argv) < 2:
		print "usage: python create_concept_dataset.py <amr_nx_graphs.p> <amr_aggregated_metadata.p>"
		return
	amr_nx_graphs_p = argv[0]
	amr_aggregated_metadata_p = argv[1]
	#Format of amr_nx_graphs
	#amr_nx_graphs = {id : [root, amr_nx_graph, sentence, alignment]}
	amr_nx_graphs = pickle.load(open(amr_nx_graphs_p, "rb"))

	#Format of amr_aggregated_metadata
	#amr_aggregated_metadata = {id : [sentence, pos, ner]}
	amr_aggregated_metadata = pickle.load(open(amr_aggregated_metadata_p, "rb"))


	training_dataset = get_training_dataset(amr_nx_graphs, amr_aggregated_metadata)
	print_to_file = True
	if print_to_file:
		for id, training_data in training_dataset.iteritems():
			print id
			for data in training_data:
				print data
			print
	pickle.dump(training_dataset, open("concept_dataset.p", "wb"))

if __name__ == "__main__":
	main(sys.argv[1:])
