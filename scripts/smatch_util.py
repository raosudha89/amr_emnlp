import sys
from collections import defaultdict
import math
from postprocess import *
import random


def dfs(child_dict, par_dict, visited, current_component, start_node):

	if start_node in child_dict or start_node in par_dict:
		for each_child in child_dict[start_node] + par_dict[start_node]:
			if each_child[0] not in visited:
				current_component.append(each_child[0])
				visited[each_child[0]] = 1
				new_visited, new_current_component = dfs(child_dict, par_dict, visited, current_component, each_child[0])
				visited = new_visited
				current_component = new_current_component
	return visited, current_component


def get_root_connected_comp(component, reverse_map_dict, child_dict, par_dict):
	roots = []
	for each_node in component:
		if each_node not in par_dict or len(par_dict[each_node]) == 0:
			roots.append(each_node)

	return roots

def pred_to_readable(predictions, node_expansions, concept_map, relation_map, n):
	"""
	Convert the numeric predictions array to a readable version
	:param predictions: The numeric predictions array
	:param concept_map: Map from concept_id to concepts
	:param relation_map: Map from relation_id to relation
	:param n: The length of the sentence
	:return:
	"""
	i = 0
	readable_pred = []
	readable_node_exp = []
	for k in range(n):
		readable_pred.append(concept_map[predictions[i]])
		readable_node_exp.append(relation_map[node_expansions[k]])
		i += 1
		for j in range(2*k):
			readable_pred.append(relation_map[predictions[i]])
			i += 1

	return readable_pred, readable_node_exp


def get_fully_connected_graph(predictions, node_expansions, n, nd_out, nd_in, nd_pair, root_index, relation_map):
	#Store the root in this array. Multiple, zero roots also checked
	roots = []

	#Store parents and children of each node
	par_dict = defaultdict(list)
	child_dict = defaultdict(list)

	#Map of id -> concept
	reverse_map_dict = {}

	#Number of concepts seen
	seen_concepts = 0

	#The ids of the concepts
	concept_ids = []

	i = 0
	for k in range(n):

		current_concept = predictions[i]
		if current_concept != "NULL":
			x = current_concept.split('_')
			if len(x) == 2:
				new_id1 = 'c' + str(seen_concepts)
				seen_concepts += 1
				reverse_map_dict[new_id1] = x[0]
				#concept_ids.append(new_id1)

				new_id2 = 'c' + str(seen_concepts)
				seen_concepts += 1
				reverse_map_dict[new_id2] = x[1]
				concept_ids.append(new_id2)

				edge = node_expansions[k]

				child_dict[new_id1].append((new_id2, edge))
				par_dict[new_id2].append((new_id1, edge))

			else:
				new_id = 'c' + str(seen_concepts)
				seen_concepts += 1
				reverse_map_dict[new_id] = predictions[i]
				concept_ids.append(new_id)
		else:
			concept_ids.append("NULL")

		i += 1

		for j in range(k):
			curr_edge = predictions[i]
			if curr_edge != "NOEDGE":
				parent = concept_ids[k]
				child = concept_ids[j]
				child_dict[parent].append((child, curr_edge))
				par_dict[child].append((parent, curr_edge))
			i += 1
		for j in range(k):
			curr_edge = predictions[i]
			if predictions[i] != "NOEDGE":
				parent = concept_ids[j]
				child = concept_ids[k]
				child_dict[parent].append((child, curr_edge))
				par_dict[child].append((parent, curr_edge))
			i += 1

	#Post-process
	reverse_map_dict, par_dict, child_dict = postprocess_main(reverse_map_dict, par_dict, child_dict,
															  nd_out, nd_in, nd_pair)

	for each_node in reverse_map_dict:
		if each_node not in par_dict:
			roots.append(each_node)

	#print child_dict
	#print par_dict
	#print reverse_map_dict
	#print
	#print roots
	#print concept_ids[root_index]

	#Find number of connected components
	components = []
	visited = {}
	for each_node in reverse_map_dict:
		if each_node in visited:
			continue
		visited[each_node] = 1
		visited, current_components = dfs(child_dict, par_dict, visited, [each_node], each_node)
		components += [current_components]


	#print len(components)
	if len(components) == 0:
		faux_root_id = "m"
		reverse_map_dict[faux_root_id] = "multi-sentence"
		return faux_root_id, child_dict, reverse_map_dict

	main_root = concept_ids[root_index]
	roots = []
	for each_component in components:
		roots += get_root_connected_comp(each_component,reverse_map_dict, child_dict, par_dict)
	c = 0
	edges_added = []
	for each_root in roots:
		if each_root == main_root:
			continue
		real_each_root = reverse_map_dict[each_root]
		real_main_root = reverse_map_dict[main_root]
		if (real_main_root, real_each_root) in nd_pair:
			relations_data = nd_pair[(real_main_root, real_each_root)]
		elif real_main_root in nd_out:
			relations_data = nd_out[real_main_root]
		elif real_each_root in nd_in and real_main_root != "and":
			relations_data = nd_in[real_each_root]
		else:
			relations_data = [(r, 1) for r in relation_map.values()]
		edge = None
		for (rel, count) in relations_data:
			if rel in edges_added or rel == "NOEDGE":
				continue
			edge = rel
			edges_added.append(edge)
			break
		if not edge:
			edge = "ARG"+str(c)
			c += 1
		par_dict[each_root].append((main_root, edge))
		child_dict[main_root].append((each_root, edge))

	return main_root, child_dict, reverse_map_dict

def amr_to_string(root, child_dict, reverse_map_dict, visited, tab_levels = 1):
	"""
	A DFS-traversal of the graph to convert it to text
	:param root: The root of the amr
	:param child_dict: An adjacency list of type {node : [(child, edge)]}
	:param reverse_map_dict: A mapping from concept short names to full names
	:param visited: List of visited nodes
	:return: String representation of AMR
	"""

	amr_string = ""

	#Recursively traverse through the rest of the graph
	for each_child in child_dict[root]:
		if each_child[0] not in visited:
			x = amr_to_string(each_child[0], child_dict, reverse_map_dict, visited + [root], tab_levels+1)
			amr_string += "\t"*tab_levels + "\t:{0} ".format(each_child[1]) + x[0]
			visited = x[1]
			visited.remove(root)
		else:
			amr_string += "\t:{0} {1}\n".format(each_child[1], each_child[0])


	#print root + string obtained from children
	if root not in visited:
		#print root, reverse_map_dict, child_dict
		amr_string = "({0} / {1}\n".format(root, reverse_map_dict[root]) + amr_string + ")"
		visited.append(root)
	else:
		amr_string = "{0}".format(root)

	return amr_string, visited


def write_amr_to_file(amr_id, raw_predictions, raw_node_expansions, concept_map, relation_map, f, nd_out, nd_in, nd_pair, root_index):
	"""
	Wrapper function that takes in raw predictions array and writes the converted amr to file
	:param amr_id: The amr_id of the AMR
	:param raw_predictions: The raw predictions array
	:param concept_map: Map of concept_label -> concept
	:param relation_map: Map of relation_label -> relation
	:param f: The output file handle
	"""

	#Get readable predictions
	n = int(math.sqrt(len(raw_predictions)))
	predictions, node_expansions = pred_to_readable(raw_predictions, raw_node_expansions, concept_map, relation_map, n)


	#Get the string representation
	root, child_dict, reverse_map_dict = get_fully_connected_graph(predictions, node_expansions, n, nd_out, nd_in, nd_pair, root_index, relation_map)
	# root, child_dict, reverse_map_dict
	out_string = amr_to_string(root, child_dict, reverse_map_dict, [])[0]


	#Write to file
	f.write("# ::id {0}\n".format(amr_id))
	f.write(out_string)
	f.write('\n')
	f.write('\n')

"""
def main(argv):

	label_dict = {'op4': 57, 'op5': 58, 'op6': 59, 'op7': 60, 'op1': 54, 'op2': 55, 'op3': 56, 'ARG3-of': 9, 'op9': 62, 'month': 52, 'manner-of': 48, 'decade': 26, 'dayperiod': 25, 'path-of': 67, 'condition-of': 22, 'instrument': 42, 'location': 45, 'poss-of': 71, 'ord-of': 64, 'prep-among': 73, 'op8': 61, 'prep-from': 79, 'prep-within': 87, 'concession-of': 20, 'li': 44, 'day': 24, 'condition': 21, 'mod': 50, 'name': 53, 'prep-by': 76, 'accompanier': 14, 'compared-to': 18, 'mode': 51, 'frequency-of': 41, 'prep-without': 88, 'domain': 32, 'frequency': 40, 'year': 114, 'prep-in': 80, 'prep-on-behalf-of': 84, 'prep-at': 75, 'prep-as': 74, 'unit': 110, 'polarity': 68, 'degree': 27, 'extent-of': 39, 'NOEDGE': 13, 'extent': 38, 'degree-of': 28, 'path': 66, 'ord': 63, 'poss': 70, 'ARG0': 2, 'ARG1': 4, 'ARG2': 6, 'ARG3': 8, 'ARG4': 10, 'ARG5': 12, 'prep-except': 77, 'weekday': 113, 'concession': 19, 'duration-of': 34, 'location-of': 46, 'prep-to': 85, 'ARG2-of': 7, 'prep-on': 83, 'consist-of': 23, 'part-of': 65, 'source': 104, 'destination': 29, 'beneficiary': 16, 'snt11': 95, 'snt10': 94, 'prep-instead-of': 82, 'direction': 30, 'medium': 49, 'season': 92, 'direction-of': 31, 'instrument-of': 43, 'prep-against': 72, 'prep-for': 78, 'topic-of': 109, 'quant-of': 91, 'value': 111, 'prep-with': 86, 'era': 35, 'time-of': 107, 'example': 36, 'snt7': 101, 'snt6': 100, 'snt5': 99, 'snt4': 98, 'snt3': 97, 'snt2': 96, 'snt1': 93, 'century': 17, 'source-of': 105, 'snt9': 103, 'snt8': 102, 'topic': 108, 'duration': 33, 'ARG1-of': 5, 'manner': 47, 'quant': 90, 'polite': 69, 'ARG4-of': 11, 'purpose': 89, 'ARG0-of': 3, 'example-of': 37, 'age': 15, 'value-of': 112, 'prep-in-addition-to': 81, 'time': 106}

	concept_dict = {'thing_include-91': 128, 'course-01': 130, 'we': 135, 'tobacco': 141, 'behind': 138, 'far': 137, 'many': 132, 'include-01': 129, 'there': 125, 'meet-01': 139, 'include-91': 126, 'meet-03': 140, 'contrast-01': 143, 'person_include-91': 127, 'course': 131, 'reason': 134, 'control-01': 142, 'person_many': 133, 'objective': 144, 'lag-01': 136, 'NULL': 1}

	predictions = [1, 1, 13, 13, 1, 13, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 132, 13, 13, 13, 13, 13, 13, 13, 13, 134, 13, 13, 13, 13, 90, 13, 13, 13, 13, 13, 1, 13, 13, 13,
13, 13, 13, 13, 13, 13, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
13, 135, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 136, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
13, 13, 137, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 6, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 139, 13, 13, 13, 13, 13, 13, 13, 13, 13, 2, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 2, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13
, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 141, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 142, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 4, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 144, 13, 13, 13, 13, 13, 13, 13, 13, 13, 70, 13, 13, 13, 13, 13, 13, 13, 50, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13
, 4, 13, 13, 13, 1, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13
, 13, 13, 13]


	print len(predictions)
	n = 20
	x = pred_to_readable(predictions, {v:k for k,v in concept_dict.items()}, {v:k for k,v in label_dict.items()}, n)

	root, child_dict, reverse_map_dict = find_root(x, n)

	print amr_to_string(root, child_dict, reverse_map_dict, [])[0]

if __name__ == "__main__":
	main(sys.argv[1:])
"""
