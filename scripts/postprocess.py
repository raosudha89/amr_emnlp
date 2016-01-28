import sys

def post_process_name(reverse_map_dict, par_dict, child_dict):

	count = 0
	new_reverse_map_dict = {}

	for each_node in reverse_map_dict:
		x = reverse_map_dict[each_node].split('_')
		if x[0] == 'date-entity':
			pass
		if len(x) >= 3 and x[1] == 'name':
			new_reverse_map_dict[each_node] = x[0]

			new_node_short_name = "n"+str(count)

			count += 1

			new_node_name = "name "

			subcount = 1
			for each in x[2:]:
				new_node_name += ":op{0} {1} ".format(subcount, each)
				subcount += 1

			new_reverse_map_dict[new_node_short_name] = new_node_name
			child_dict[each_node].append((new_node_short_name, "name"))
			par_dict[new_node_short_name].append((each_node, "name"))

		elif len(x) == 4 and x[0] == 'date-entity':
			new_name_str = "date-entity "
			if x[1] != 'X':
				new_name_str += ":year {0} ".format(x[1])
			if x[2] != 'X':
				new_name_str += ":month {0} ".format(x[2])
			if x[3] != 'X':
				new_name_str += ":day {0} ".format(x[3])

			new_reverse_map_dict[each_node] = new_name_str


		else:
			new_reverse_map_dict[each_node] = reverse_map_dict[each_node]

	return new_reverse_map_dict, par_dict, child_dict

"""
def post_process_polarity(reverse_map_dict, par_dict, child_dict):

	count = 0
	new_reverse_map_dict = {}

	for each_node in reverse_map_dict:
		x = reverse_map_dict[each_node].split('_')



		else:
			new_reverse_map_dict[each_node] = reverse_map_dict[each_node]

	return new_reverse_map_dict, par_dict, child_dict
"""


def post_process_tq(reverse_map_dict, par_dict, child_dict):

	count = 0
	new_reverse_map_dict = {}

	for each_node in reverse_map_dict:
		x = reverse_map_dict[each_node].split('_')
		if len(x) == 2 and x[1] == '-':
			new_reverse_map_dict[each_node] = x[0] + " :polarity -"

		else:
			new_reverse_map_dict[each_node] = reverse_map_dict[each_node]

		"""
		elif len(x) == 2 and x[0][-9:] == '-quantity':
			#new_reverse_map_dict[each_node] = x[0]

			new_node_short_name = "t"+str(count)
			new_node_short_name2 = "s"+str(count)

			count += 1

			new_node_name = x[0]
			new_node_name2 = x[1]

			subcount = 1
			#for each in x[2:]:
			#	new_node_name += ":op{0} {1} ".format(subcount, each)
			#	subcount += 1

			new_reverse_map_dict[new_node_short_name] = new_node_name
			new_reverse_map_dict[new_node_short_name2] = new_node_name2
			child_dict[new_node_short_name].append((new_node_short_name2, "unit"))
			par_dict[new_node_short_name2].append((new_node_short_name, "unit"))

			if each_node in par_dict:
				par = [z[0] for z in par_dict[each_node]]
				del par_dict[each_node]
				for each_par in par:
					new_child = [z for z in child_dict[each_par] if z[0] != each_node]
					child_dict[each_par] = new_child

			if each_node in child_dict:
				children = [z[0] for z in child_dict[each_node]]
				del child_dict[each_node]
				for each_child in children:
					new_par = [z for z in par_dict[each_child] if z[0] != each_node]
					par_dict[each_child] = new_par
		"""


	return new_reverse_map_dict, par_dict, child_dict


#def post_process_others():





def postprocess_main(reverse_map_dict, par_dict, child_dict, nd_out, nd_in, nd_pair):

	r, p, c = post_process_name(reverse_map_dict, par_dict, child_dict)
	#r, p, c = post_process_polarity(r, p, c)
	r, p, c = post_process_tq(r, p, c)
	#r, p, c = post_process_others(reverse_map_dict, par_dict, child_dict, nd_out, nd_in, nd_pair)

	return r, p, c
