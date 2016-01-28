import sys
import cPickle as pickle
from collections import defaultdict

#d0 = pickle.load(open("../data/amr-release-1.0-training-proxy/nodes_relation_dict.p", 'rb'))[0]
#d1 = pickle.load(open("../data/amr-release-1.0-training-proxy/nodes_relation_dict.p", 'rb'))[1]
#d2 = pickle.load(open("../data/amr-release-1.0-training-proxy/nodes_relation_dict.p", 'rb'))[2]
#kbest_dep_parse = pickle.load(open("../data/amr-release-1.0-test-bolt/kbest_dep_parse.p",'rb'))

def dict_to_list(d):

	l = defaultdict(list)
	for node in d:
		for key in d[node]:
			l[node].append((key, d[node][key]))
		l[node] = sorted(l[node], reverse=True, key=lambda x: x[1])

	return l

def is_root(c_short, pred_dict):
	if len(pred_dict[c_short]) == 0:
		return True

def create_dataset(amr_nx_graphs, concept_data):

	dataset = {}
	dis_dict = {}
	count = 0
	super_count = 0
	nodes_relation_dict_out = defaultdict(lambda: defaultdict(int))
	nodes_relation_dict_in = defaultdict(lambda: defaultdict(int))
	nodes_relation_dict_pair = defaultdict(lambda: defaultdict(int))
	super_dict = {}

	for id, value in amr_nx_graphs.iteritems():

		edges_dict_dataset = {}

		[root, amr_nx_graph, sentence, alignments] = value
		edges = amr_nx_graph.edges(data=True)
		concepts = concept_data[id]
		edges_dict = {(x[0], x[1]): x[2]['relation'] for x in edges}

		root_found = False

		#Get all pairwise concepts
		for i in range(len(concepts)):
			x = concepts[i][2].split('_')
			y = concepts[i][3].split('_')

			c_i = concepts[i][2]
			word_i = concepts[i][0]
			c_i_short = concepts[i][3]

			if c_i == "NULL":
				continue

			#Check if root
			if root == c_i_short:
				if root_found:
					print id
					print "ALERT : TWO ROOTS FOUND"

				edges_dict_dataset[(-1, i, "ROOT", c_i)] = "ROOT"
				root_found = True


			if len(x) >= 2:
				try:
					uscore_edge = edges_dict[(y[0], y[1])]
					nodes_relation_dict_out[x[0]][uscore_edge] += 1
					nodes_relation_dict_pair[x[1]][uscore_edge] += 1
					nodes_relation_dict_pair[(x[0], x[1])][uscore_edge] += 1
					edges_dict_dataset[(i,i, x[0], x[1])] = uscore_edge

					if root == y[0]:
						if root_found:
							print id
							print "ALERT : TWO ROOTS FOUND"
						edges_dict_dataset[(-1, i, "ROOT", c_i)] = "ROOT"
						root_found = True
				except KeyError:
					print "Error1"
					pass
			for j in range(len(concepts)):

				if i == j:
					continue

				c_j = concepts[j][2]
				word_j = concepts[j][0]
				c_j_short = concepts[j][3]

				if c_j == "NULL":
					continue

				t = (c_i_short, c_j_short)

				if t in edges_dict:
					super_count += 1
					relation = edges_dict[t]
					edges_dict_dataset[(i, j, c_i, c_j)] = edges_dict[t]
					nodes_relation_dict_out[c_i][relation] += 1
					nodes_relation_dict_in[c_j][relation] += 1

					pos1 = concepts[i][1]
					pos2 = concepts[j][1]

					if relation not in super_dict:
						super_dict[relation] = 0
					super_dict[relation] += 1

					nodes_relation_dict_pair[(c_i, c_j)][relation] += 1

				else:
					nodes_relation_dict_pair[(c_i, c_j)]["NOEDGE"] += 1

		dataset[id] = edges_dict_dataset
		if not root_found:
			print id
			print "ALERT : NO ROOT FOUND"
	print count, super_count
	nodes_relation_dicts = [dict_to_list(nodes_relation_dict_out), dict_to_list(nodes_relation_dict_in),
							dict_to_list(nodes_relation_dict_pair)]

	sorted_list = sorted([(x, super_dict[x]) for x in super_dict], key = lambda x:x[1], reverse = True)
	for each in sorted_list:
		print each[0], '\t', each[1]
	#for each_pos_pair in super_dict:
	#	sorted_list = sorted([(x, super_dict[each_pos_pair][x]) for x in super_dict[each_pos_pair]], key = lambda x:x[1], reverse = True)
	#	print each_pos_pair
	#	print sorted_list
	#	print
	#	print


	return dataset, nodes_relation_dicts



def main(argv):

	if len(argv) < -1:
		raise Exception("Incorrect number of arguments. Usage : python create_relation_dataset.py "
						"<amr_nx_graphs.p> <concept_dataset.p> <train_flag>")

	amr_nx_graphs_p = argv[0] #"../data/amr-release-1.0-training-proxy/amr_nx_graphs.p"
	concept_training_dataset_p = argv[1]  #"../data/amr-release-1.0-training-proxy/concept_dataset.p"
	train_flag = True if int(argv[2]) == 1 else False

	#Load the amr_nx_graphs
	amr_nx_graphs = pickle.load(open(amr_nx_graphs_p, "rb"))

	#Load the concept training data set
	concept_training_dataset = pickle.load(open(concept_training_dataset_p, "rb"))

	#Create the relation training dataset and the (concept pair) -> relation dicts
	dataset, nodes_relation_dicts = create_dataset(amr_nx_graphs, concept_training_dataset)

	pickle.dump(dataset, open("relation_dataset.p", "wb"))

	if train_flag:
		pickle.dump(nodes_relation_dicts, open("nodes_relation_dict.p", "wb"))

	print_to_file = False

	if print_to_file:
		for each in nodes_relation_dicts[2]:
			print each, "\t", nodes_relation_dicts[2][each]
			#print nodes_relation_dicts[each]

if __name__ == "__main__":
	main(sys.argv[1:])
