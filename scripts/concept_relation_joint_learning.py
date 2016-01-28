import sys, os
import cPickle as pickle
import time
from smatch_util import *
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import profile
from evaluate_concepts import *
import re
import datetime
import networkx as nx

if not os.environ.has_key('VW_PYTHON_PATH'):
	print "Please set the env var VW_PYTHON_PATH to point to location of vowpal_wabbit/python"
	sys.exit()
VW_PYTHON_PATH = os.environ['VW_PYTHON_PATH']

sys.path.append(VW_PYTHON_PATH)

span_concept_dict_p = None
vnpb_words_concepts_dict_p = None

import pyvw

edgeLabelsList = []
edgeLabels = {}
dep_parse = {}
gold_relation_dict = {}
nodes_relation_dic = {}
concept_labels = {"NULL": 1}
concept_map = {1: "NULL"}
relation_map = {}
last_used_label = 1
training_id_dict = {}
example_cache = {}
seen_dict = {}
flag = True
prev_sent_id = ""
nodes_relation_dict_out = {}
nodes_relation_dict_in = {}
nodes_relation_dict_pair = {}
dep_parse_nx = {}

class Span:
	def __init__(self, words, pos, word_positions, ner, concept="NULL"):
		self.words = words
		self.pos = pos
		self.word_positions = word_positions
		self.ner = ner
		self.concept = concept

class Sentence:

	def __init__(self, id, spans):
		self.id =id
		self.spans = spans


def read_amr(f):
	"""
	Read the original aligned amr from the file f
	:param f: The input file
	:return:
	"""
	amr_dict = {}
	current_amr = ""
	flag = 0
	for each_line in f:

		if each_line.startswith("# ::id"):
			id = each_line.strip().split()[2]
		elif each_line.startswith("# ::snt") or each_line.startswith("# ::save-data") or each_line.startswith("# ::tok"):
			continue
		elif each_line.startswith("# ::alignments"):
			flag = 1
			continue

		if flag == 1:
			if each_line.strip() == "":
				flag = 0
				amr_dict[id] = current_amr
				current_amr = ""
			else:
				current_amr += each_line

	return amr_dict



#TODO clean this!

def get_K_best_concepts(span, span_concept_dict=None, vnpb_words_concepts_dict=None):
	#Get the top k concepts aligned with span.words
	K = 5
	if span_concept_dict is None: span_concept_dict = pickle.load(open(span_concept_dict_p, "rb"))
	if span_concept_dict.has_key(span.words):
		return [ (concept, count) for (concept, count) in span_concept_dict[span.words]][:K]
	if vnpb_words_concepts_dict is None: vnpb_words_concepts_dict = pickle.load(open(vnpb_words_concepts_dict_p, "rb"))
	if vnpb_words_concepts_dict.has_key(span.words):
		return [ (concept, 1) for concept in vnpb_words_concepts_dict[span.words]]
	concept = ""	
	if "<" and ">" in span.ner:
		r = re.search("(.*?)<(.*?)>(.*?)", span.ner)	
		ner = r.group(2).lower()
		if ner == "date":
			ner = "date-entity"
			date_words = span.words.strip().replace(",","")
			date_words = "/".join(date_words.split())
			try:
				d = datetime.datetime.strptime(date_words, "%B/%d/%Y")
				concept = ner + "_" + str(d.year) + "_" + str(d.month).lstrip('0') + "_" + str(d.day).lstrip('0')
			except:
				try:
					d = datetime.datetime.strptime(date_words, "%d/%B/%Y")	
					concept = ner + "_" + str(d.year) + "_" + str(d.month).lstrip('0') + "_" + str(d.day).lstrip('0')
				except:
					try:
						d = datetime.datetime.strptime(date_words, "%B/%Y")	
						concept = ner + "_" + str(d.year) + "_" + str(d.month).lstrip('0') + "_X"
					except:
						if re.search("([0-9]{4})",span.words.split()[0]):
							yyyy = span.words.split()[0]
							concept = ner + "_" + yyyy + "_X_X"
						else:
							concept = ner + "_"
							concept += "_".join("\"" + w + "\"" for w in span.words.split())  
		else:
			if ner == "location": ner = "country"
			concept = ner + "_name_"
			concept += "_".join("\"" + w + "\"" for w in span.words.split())
		return [(concept, 1), ("NULL", 1)]

	is_date = re.search("([0-9]*)-([0-9]*)-([0-9]*)", span.words.split()[0])
	if is_date:
		yyyy = is_date.group(1)
		mm = is_date.group(2)
		dd = is_date.group(3)
		concept = "date-entity_" + yyyy + "_" + mm + "_" + dd
		return [(concept, 1), ("NULL", 1)]
	
	is_date = re.search("([0-9]{6})", span.words.split()[0])
	if is_date:
		date = span.words.split()[0]
		yyyy = "20" + date[:2]
		mm = date[2:4]
		dd = date[4:]
		concept = "date-entity_" + yyyy + "_" + mm + "_" + dd
		return [(concept, 1), ("NULL", 1)]
	
	stemmer=PorterStemmer()
	span_stem = stemmer.stem(span.words)
	wordnet_lemmatizer = WordNetLemmatizer()
	if span.pos[0] == "V":
		span_lemma =  wordnet_lemmatizer.lemmatize(span.words.lower(), pos='v')
	else:
		span_lemma =  wordnet_lemmatizer.lemmatize(span.words.lower())
	if span.pos[0] == "V":
		return [(str(span_lemma)+"-01", 1), ("NULL", 1)]
	
	return [(str(span_lemma), 1), ("NULL", 1)]

def concept2label(concept):
	global concept_labels
	global last_used_label
	global concept_map
	if not concept_labels.has_key(concept):
		concept_labels[concept] = last_used_label + 1
		concept_map[last_used_label + 1] = concept
		last_used_label += 1
	return concept_labels[concept]

def label2concept(_label):
	global concept_labels
	for concept, label in concept_labels.iteritems():
		if label == _label:
			return concept

def label2relation(_label):
	global edgeLabels
	for relation, label in edgeLabels.iteritems():
		if label == _label:
			return relation

def get_words(sentence, i):
	return "<s>" if i < 0 else "</s>" if i >= len(sentence.spans) else sentence.spans[i].words

def get_pos(sentence, i):
	return "<s>" if i < 0 else "</s>" if i >= len(sentence.spans) else sentence.spans[i].pos

def get_concept_features(concept):
	return concept.split('-')

def eraseAnnotations(sentence):
	erasedSentenceSpans = []
	for i in xrange(len(sentence.spans)):
		#print cleaned_par
		erasedSentenceSpans.append(Span(sentence.spans[i].words, sentence.spans[i].pos, sentence.spans[i].word_positions, sentence.spans[i].ner, "NULL"))
	return Sentence(sentence.id, erasedSentenceSpans)


def getKbestEdges(parent_node, child_node):

	global nodes_relation_dict_out
	global nodes_relation_dict_in
	global nodes_relation_dict_pair

	#Get the top k concepts aligned with span.words
	K = 5
	t1, t2, t3 = [], [], []
	t = (parent_node, child_node)

	#parent_node = _parent_node.split('@')[0]
	#child_node = _child_node.split('@')[0]
	#if nodes_relation_dict is None:
	#    nodes_relation_dict = pickle.load(open("nodes_relation_dict.p", "rb"))
	if parent_node in nodes_relation_dict_out:
		t1 = [relation for (relation, count) in nodes_relation_dict_out[parent_node]]#[:K]
	if child_node in nodes_relation_dict_in:
		t2 = [relation for (relation, count) in nodes_relation_dict_in[child_node]]#[:K]
	if t in nodes_relation_dict_pair:
		t3 = [relation for (relation, count) in nodes_relation_dict_pair[t]]#[:K]

	if parent_node == "and":
		t3 = []

	#print t
	#print word2vecsuggestions[t]
	#if len(t3) == 0:
	#	ret = list(set(t1+t2)) #+ ["mod", "ARG0", "ARG1", "ARG2", "ARG1-of", "ARG0-of", "ARG2-of"]))
	#else:
	#	ret = list(set(t3+["NOEDGE"]))
	ret = list(set(t1+t2+t3+["NOEDGE"]))


	if len(ret) == 0:
		return -1

	return ret

def dep_path(sentence, node1, node2, dist):
	global dep_parse
	#print node1, node2, dist
	dep_parse_id = sentence.id
	parse_list = dep_parse[dep_parse_id]
	for src in parse_list.keys():
		for (tgt, rel) in parse_list[src]:
			if src == node1:
				if tgt == node2:
					return rel
			if tgt == node1:
				if src == node2:
					return rel
	for src in parse_list.keys():
		for (tgt, rel) in parse_list[src]:
			if src == node1:
				if dist > 1:
					p = dep_path(sentence, tgt, node2, dist-1)
					return p + '_' + rel
			if tgt == node1:
				if dist > 1:
					q = dep_path(sentence, src, node2, dist-1)
					return q + '_' + rel

def has_dep_relation(sentence, node1, node2, dist):
	global dep_parse
	#print node1, node2, dist
	dep_parse_id = sentence.id
	parse_list = dep_parse[dep_parse_id]
	for src in parse_list.keys():
		for (tgt, rel) in parse_list[src]:
			if src == node1:
				if tgt == node2:
					return True
			if tgt == node1:
				if src == node2:
					return True
	for src in parse_list.keys():
		for (tgt, rel) in parse_list[src]:
			if src == node1:
				if dist > 1:
					if has_dep_relation(sentence, tgt, node2, dist-1):
						return True
			if tgt == node1:
				if dist > 1:
					if has_dep_relation(sentence, src, node2, dist-1):
						return True
	return False

class ConceptRelationLearning(pyvw.SearchTask):
	def __init__(self, vw, sch, num_actions):

		global edgeLabelsList
		global edgeLabels
		global concept_labels
		global last_used_label
		global relation_map
		global nodes_relation_dict_out

		pyvw.SearchTask.__init__(self, vw, sch, num_actions)
		#sch.set_options( sch.AUTO_HAMMING_LOSS | sch.IS_LDF | sch.AUTO_CONDITION_FEATURES )
		sch.set_options( sch.AUTO_HAMMING_LOSS | sch.IS_LDF)
		self.span_concept_dict = pickle.load(open(span_concept_dict_p, "rb"))
		self.vnpb_words_concepts_dict = pickle.load(open(vnpb_words_concepts_dict_p, "rb"))
		edgeLabelsList = sorted(list(set([x[0] for key in nodes_relation_dict_out for x in nodes_relation_dict_out[key]]
		 + ["NOEDGE"])))

		for i in xrange(len(edgeLabelsList)):
			edgeLabels[edgeLabelsList[i]] = i + 2
			relation_map[i+2] = edgeLabelsList[i]

		last_used_label += len(edgeLabels) + 10
		self.cached_concept_examples = {}
		self.cached_relation_examples = {}


	def make_concept_example(self, sentence, k, concept, count, index, predictions):
		is_best = 0
		if index == 0:
			is_best = 1

		curr_dp = dep_parse[sentence.id]

		words_positions = sentence.spans[k].word_positions
		dep_edges = []
		for each_pos in words_positions:
			if each_pos+1 in curr_dp:
				dep_edges = sorted([x[1] for x in curr_dp[each_pos+1]])

		"""
		rel1 = []
		for j in range((k-1)*(k-1)+1, k*k):
			if not predictions[j]:
				continue
			rel = relation_map[predictions[j]]
			if rel != "NOEDGE":
				rel1.append(rel)
	
		rel2 = []
		for j in range((k-2)*(k-2)+1, (k-1)*(k-1)):
			if not predictions[j]:
				continue
			rel = relation_map[predictions[j]]
			if rel != "NOEDGE":
				rel2.append(rel)
		"""

		a = ["s@"+str(j)+"="+str(s) for j,s in enumerate(concept.split('_'))] + ['ib='+str(is_best)] + \
			['c@-1=' + label2concept(predictions[(k-1)*(k-1)]) if k>=1 else 'START' + 'c@-2' + label2concept(predictions[(k-2)*(k-2)]) if k>=2 else 'START']
			#+ ['r@-1'+str(j)+'='+str(r) for j,r in enumerate(rel1) ] + ['r@-2'+str(j)+'='+str(r) for j,r in enumerate(rel2) ]
	
		b = [ 'w=' + sentence.spans[k].words.replace(" ", "_")]
		c = [ "w@-" + str(delta) + "=" + get_words(sentence,k-delta) for delta in [1,2]] + [ "w@+" + str(delta) + "=" + get_words(sentence,k+delta) for delta in [1,2]]
		d = ['p=' + sentence.spans[k].pos.replace(" ", "_")]
		e = [ "p@-" + str(delta) + "=" + get_pos(sentence,k-delta) for delta in [1,2]] + [ "p@+" + str(delta) + "=" + get_pos(sentence,k+delta) for delta in [1,2]]
		g = [ "sp@"+str(j)+"="+str(w == stopwords.words('english')) for j,w in enumerate(sentence.spans[k].words.split()) ]
		h = ['df=' + '_'.join(dep_edges)]
		
		f = lambda: {'a':a, 'b':b, 'c':c, 'd':d, 'e':e, 'g':g, 'h':h}
		ex = self.example(f, labelType=self.vw.lCostSensitive)
		label = concept2label(concept)
		ex.set_label_string(str(label) + ":0")
		return ex

	def predict_concept(self, sentence, k, i, predictions):
		#predict concept for the kth item and store it in index i of predictions
		span = sentence.spans[k]
		k_best_concepts = get_K_best_concepts(span, self.span_concept_dict, self.vnpb_words_concepts_dict)
		#predictions[i] = concept2label(k_best_concepts[0][0])
		#return

		oracle = [v for v, (concept, count) in enumerate(k_best_concepts) if concept == span.concept]
		#predictions[i] = concept2label(oracle[k_best_concepts[0][0]])
		#return

		examples = [self.make_concept_example(sentence, k, concept, count, v, predictions) for v, (concept, count)
					in enumerate(k_best_concepts)]

		"""
		#condition on 5 edges each to k-1 and k-2
		condition_list = []
		l = 0
		names = ['a', 'b', 'c', 'd', 'e']
		for j in range((k-1)*(k-1)-1, k*k):
			if predictions[j] != edgeLabels["NOEDGE"]:
				condition_list += [(j+1, names[l])]
				l += 1
				if l >= 5:
					break
		l = 0
		names = ['f', 'g', 'h', 'i', 'j']
		for j in range((k-2)*(k-2)-1, (k-1)*(k-1)):
			if predictions[j] != edgeLabels["NOEDGE"]:
				condition_list += [(j+1, names[l])]
				l += 1
				if l >= 5:
					break
		"""

		pred = self.sch.predict(examples=examples,
								my_tag=i+1,
								oracle=oracle,
								condition=[((k-1)*(k-1),'a'), (((k-2)*(k-2),'b'))],
								#condition = condition_list,
								learner_id = 2
							)
		predictions[i] = concept2label(k_best_concepts[pred][0])


	def make_relation_example(self, sentence, k, j, edge_label, predictions, uscore_flag = False):

		n = len(sentence.spans)
		if uscore_flag:
			#edge_label_cleaned = edge_label.split('-')

			#c1 = sentence.spans[k].words.lower()
			#c2 = sentence.spans[j].words.lower()
			c1, c2 = label2concept(predictions[k*k]).split('_')

			#Previous concept
			cprev1 = label2concept(predictions[(k-1)*(k-1)]) if k>=1 else 'START'
			#cnext1 = label2concept(predictions[(k+1)*(k+1)]) if k<=n-2 else 'END'
			#Word
			w1 = sentence.spans[k].words.lower()

			#Words in context spans
			lwk = sentence.spans[k-1].words.lower() if k > 0 else '-'
			rwk = sentence.spans[k+1].words.lower() if k < n-1 else '-'

			#Pos tags and word postions
			pos1 = sentence.spans[k].pos
			w_pos1 = sentence.spans[k].word_positions

			isnumc1 = c1.isdigit()
			isnumc2 = c2.isdigit()

			#currdp = dep_path(sentence, w_pos1[0]+1, w_pos2[0]+1, len(sentence.spans) + 1)
			#print w1, w2, currdp


			deprel_forward = '-'
			#deprel_reverse = '-'
			deprel_dict = dep_parse[sentence.id]
			for i in range(len(w_pos1)):
				each_position = w_pos1[i]
				for j in range(len(w_pos1)):
					each_position2= w_pos1[j]
					if each_position+1 in deprel_dict:
						for each in deprel_dict[each_position+1]:
							if each[0] == each_position2+1:
								deprel_forward = each[1]
								break
					if deprel_forward != '-':
								break
				if deprel_forward != '-':
							break

			a = ["l=" + edge_label]
			b = ['cprev1=' + cprev1]
			c = ['c1=' + c1] + ['c2=' + c2] + ['c1c2=' + c1 + '_' + c2]
			d = ['w1=' + w1]
			e =	["pos1=" + pos1]
			f = ["deprel_forward=" + deprel_forward]
			g = ['cnext1=1']

		else:
			global edgeLabels

			#edge_label_cleaned = edge_label.split('-')

			#c1 = sentence.spans[k].words.lower()
			#c2 = sentence.spans[j].words.lower()
			c1 = label2concept(predictions[k*k])
			c2 = label2concept(predictions[j*j])

			#Previous concept
			cprev1 = label2concept(predictions[(k-1)*(k-1)]) if k >= 1 else 'START'
			cprev2 = label2concept(predictions[(j-1)*(j-1)]) if j >= 1 else 'START'
			cnext1 = label2concept(predictions[(k+1)*(k+1)]) if k <= n - 2 else 'END'
			cnext2 = label2concept(predictions[(j+1)*(j+1)]) if j <= n - 2 else 'END'

			w1 = sentence.spans[k].words.lower()
			w2 = sentence.spans[j].words.lower()

			#Words in context spans
			lwk = sentence.spans[k-1].words.lower() if k > 0 else '-'
			lwj = sentence.spans[j-1].words.lower() if j > 0 else '-'
			rwk = sentence.spans[k+1].words.lower() if k < n-1 else '-'
			rwj = sentence.spans[j+1].words.lower() if j < n-1 else '-'

			pos1 = sentence.spans[k].pos
			pos2 = sentence.spans[j].pos

			w_pos1 = sentence.spans[k].word_positions
			w_pos2 = sentence.spans[j].word_positions

			idx1 = k
			idx2 = j

			reverse_edge = '-'
			jm1_j = '-'
			jm2_j = '-'
			jm3_j = '-'
			jm4_j = '-'

			k_km1 = '-'
			k_km2 = '-'
			k_km3 = '-'
			k_km4 = '-'
			if k < j:
				reverse_edge = edgeLabelsList[predictions[j*j+k+1]-2]
				if k >= 1:
					k_km1 = edgeLabelsList[predictions[k*k+k]-2]
				if k >= 2:
					k_km2 = edgeLabelsList[predictions[k*k+k-1]-2]
				if k >= 3:
					k_km3 = edgeLabelsList[predictions[k*k+k-2]-2]
				if k >= 4:
					k_km4 = edgeLabelsList[predictions[k*k+k-3]-2]
			else:
				if j >= 1:
					jm1_j = edgeLabelsList[predictions[j*j+2*j]-2]
				if j >= 2:
					jm2_j = edgeLabelsList[predictions[j*j+2*j-1]-2]
				if j >= 3:
					jm3_j = edgeLabelsList[predictions[j*j+2*j-2]-2]
				if j >= 4:
					jm4_j = edgeLabelsList[predictions[j*j+2*j-3]-2]


			isnumc1 = c1.isdigit()
			isnumc2 = c2.isdigit()

			dis = str(abs(idx1 - idx2))
			if idx1 > idx2:
				dir_edge = 'r'
			else:
				dir_edge = 'l'


			#currdp = dep_path(sentence, w_pos1[0]+1, w_pos2[0]+1, len(sentence.spans) + 1)
			#print w1, w2, currdp


			deprel_forward = '-'
			#deprel_reverse = '-'
			deprel_dict = dep_parse[sentence.id]
			for each_position in w_pos1:
				for each_position2 in w_pos2:
					if each_position+1 in deprel_dict:
						for each in deprel_dict[each_position+1]:
							if each[0] == each_position2+1:
								deprel_forward = each[1]

								break
					if deprel_forward != '-':
								break
				if deprel_forward != '-':
							break

			a = ["l=" + edge_label]
			b = ['cprev1=' + cprev1] + ['cprev2=' + cprev2]
			c = ['c1=' + c1] + ['c2=' + c2] + ['c1c2='+c1+'_'+c2]
			d = ['w1=' + w1] + ['w2=' + w2] + ['w1w2=' + w1 + '_' + w2]
			e = ["pos1pos2=" + pos1 + '_' + pos2] + ["pos1=" + pos1] + ["pos2=" + pos2]
			f =	["deprel_forward=" + deprel_forward] + ["dir=" + dir_edge]
			g = ['cnext1=' + cnext1] + ['cnext2=' + cnext2]


		f = {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f, 'g': g}

		ex = self.vw.example(f, labelType=self.vw.lCostSensitive)
		label = edgeLabels[edge_label]
		ex.set_label_string(str(label)+":0")
		return ex

	def predict_relation(self, sentence, k, j, i, prediction):
		"""
		The predict relation function
		:param sentence: The sentence represented by spans
		:param k: The (prospective) parent concept
		:param j: The (prospective) child concept
		:param i: The position in predictions array where this is happening
		:param prediction: The prediction array
		:return:
		"""

		#print "ENTERED"
		global edgeLabelsList
		global edgeLabels
		global gold_relation_dict
		global example_cache
		global flag


		#Get the parent and the child for which we are making the predictions from the predictions array
		par_concept_index = k*k
		child_concept_index = j*j

		par_concept = label2concept(prediction[par_concept_index])
		child_concept = label2concept(prediction[child_concept_index])

		#No relation exists if one of the parent or child concepts is NULL
		if par_concept == "NULL" or child_concept == "NULL":
			#print "PAR OR CHILD NULL"
			prediction[i] = edgeLabels["NOEDGE"]
			return



		#Gold relation
		t = (k, j, par_concept, child_concept)
		if sentence.id in gold_relation_dict and t in gold_relation_dict[sentence.id]:
			relation = gold_relation_dict[sentence.id][t]
		else:
			relation = "NOEDGE"

		dep_rel_flag = False
		for each_word in sentence.spans[k].word_positions:
			for each_word2 in sentence.spans[j].word_positions:
				if has_dep_relation(sentence, each_word2+1, each_word+1, 2):
					dep_rel_flag = True
			if dep_rel_flag:
				break

		one_dep_rel_flag = False
		dep_rel_nx = dep_parse_nx[sentence.id][1]
		for each_word in sentence.spans[k].word_positions:
			for each_word2 in sentence.spans[j].word_positions:
				try:
					label = dep_rel_nx[each_word+1][each_word2+1]['label']
					one_dep_rel_flag = True
					#print "Good"
				except (nx.exception.NetworkXError, KeyError):
					#print "Oops"
					continue



			if one_dep_rel_flag:
				break


		if not dep_rel_flag:
			prediction[i] = edgeLabels["NOEDGE"]
			return

		#Get k-best
		k_best = getKbestEdges(par_concept, child_concept)
		if one_dep_rel_flag:
			k_best.remove("NOEDGE")

		if k_best == -1 or k_best == []:
			k_best = edgeLabelsList


		try:
			examples = example_cache[sentence.id][(k,j)][(par_concept, child_concept)]
		except KeyError:
			examples = [self.make_relation_example(sentence, k, j, edge_label, prediction)
						for edge_label in k_best]
			if sentence.id not in example_cache:
				example_cache[sentence.id] = {}
			if (k,j) not in example_cache[sentence.id]:
				example_cache[sentence.id][(k,j)] = {}
			example_cache[sentence.id][(k,j)][(par_concept, child_concept)] = examples


		condition_list = [(k*k+1, 'c'), (j*j+1, 'c'), (k*k-2*k+2, 'b'), (j*j-2*j+2, 'b'),
						  (k*k+2*k+2, 'g'), (j*j+2*j+2, 'g')]#, (k*k-2*k+2, 'x'), (j*j-2*j+2, 'y')]

		#if k < j:
			#condition_list += [(j*j+k+2, 'e')]
			#if k >= 1:	condition_list += [(k*k+k+1, 'f')]
			#if k >= 2:	condition_list += [(k*k+k, 'g')]
			#if k >= 3:	condition_list += [(k*k+k-1, 'h')]
			#if k >= 4:	condition_list += [(k*k+k-2, 'i')]

		#else:
			#if j >= 1:	condition_list += [(j*j+2*j+1, 'j')]
			#if j >= 2:	condition_list += [(j*j+2*j, 'k')]
			#if j >= 3:	condition_list += [(j*j+2*j-1, 'l')]
			#if j >= 4:	condition_list += [(j*j+2*j-2, 'm')]


		#Set oracle..
		oracle = [v for v, _label in enumerate(k_best) if _label == relation]
		#And predict!
		pred = self.sch.predict(examples=examples,
								my_tag=i+1,
								oracle=oracle,
								condition=condition_list,
								learner_id=1
								)
		#Return prediction to put in prediction[i]
		#if not flag:
		#	print k_best
		#	print par_concept, child_concept, k_best[pred]
		prediction[i] = edgeLabels[k_best[pred]]
		return

	def predict_relation_exp(self, sentence, k, node_expansions, prediction):

		global gold_relation_dict
		global flag

		n = len(node_expansions)

		concept = label2concept(prediction[k*k])
		par_concept, child_concept = concept.split('_')
		k_best = getKbestEdges(par_concept, child_concept)
		t = (k,k, par_concept, child_concept)
		if sentence.id in gold_relation_dict and t in gold_relation_dict[sentence.id]:
			relation = gold_relation_dict[sentence.id][t]
		else:
			relation = "NOEDGE"

		k_best = getKbestEdges(par_concept, child_concept)
		if "NOEDGE" in k_best:
			k_best.remove("NOEDGE")

		if par_concept == "person" and child_concept[:4] == "have":
			k_best = ["ARG0-of"]

		if len(k_best) == 0:
			k_best = ["ARG0", "ARG1", "ARG2"]

		try:
			examples = example_cache[sentence.id][(k,k)][(par_concept, child_concept)]
		except KeyError:
			examples = [self.make_relation_example(sentence, k, k, edge_label, prediction, True)
						for edge_label in k_best]
			if sentence.id not in example_cache:
				example_cache[sentence.id] = {}
			if (k,k) not in example_cache[sentence.id]:
				example_cache[sentence.id][(k,k)] = {}
			example_cache[sentence.id][(k,k)][(par_concept, child_concept)] = examples

		condition_list = [(k*k+1, 'c'), (k*k-2*k+2, 'b'), (k*k+2*k+2, 'g')]

		#Set oracle..
		oracle = [v for v, _label in enumerate(k_best) if _label == relation]
		#And predict!
		pred = self.sch.predict(examples=examples,
								my_tag=n*n+k+1,
								oracle=oracle,
								condition=condition_list,
								learner_id=1
								)
		#if not flag:
		#	print concept, k_best[pred]
		node_expansions[k] = edgeLabels[k_best[pred]]
		return

	def make_root_example(self, sentence, k, predictions):

		concept = label2concept(predictions[k*k])
		pos_tag = sentence.spans[k].pos
		word_positions = sentence.spans[k].word_positions
		words = sentence.spans[k].words
		shortest_dep_path_len = len(sentence.spans) + 10

		deprel_dict = dep_parse[sentence.id]
		is_dep_root = False
		for word_position in word_positions:
			if deprel_dict.has_key(0) and (word_position+1, "root") in deprel_dict[0]:
				is_dep_root = True

		#current_dep_parse = dep_parse[sentence.id][0]
		#shortest_dep_path = ["NULL"]

		#for each_position in word_positions:
		#	try:
		#		dep_path = nx.shortest_path(current_dep_parse, source=each_position+1, target=0)
		#		if len(dep_path) < shortest_dep_path_len:
		#			shortest_dep_path_len = len(dep_path)
		#			shortest_dep_path = dep_path
		#	except (KeyError, nx.exception.NetworkXError, nx.exception.NetworkXNoPath):
				continue

		#print shortest_dep_path
		#if shortest_dep_path != ["NULL"]:
		#	dep_path_edges = '_'.join([current_dep_parse[shortest_dep_path[i]][shortest_dep_path[i+1]]['label']
		#						for i in range(shortest_dep_path_len - 1)])
		#else:
		#	dep_path_edges = "NULL"

		#Word

		a = ['c=' + concept]
		b = ['pos=' + pos_tag]
		#c = ['dpath=' + dep_path_edges]
		d = ['words=' + words]
		e = ["isdeproot=" + str(is_dep_root)]

		#f = {'a': a, 'b': b, 'c': c, 'd': d, 'e': e}
		f = {'a': a, 'b': b, 'd': d, 'e': e}

		ex = self.vw.example(f, labelType=self.vw.lCostSensitive)
		ex.set_label_string(str(k)+":1")
		return ex

	def predict_root(self, sentence, predictions):

		global gold_relation_dict

		n = len(sentence.spans)
		#Gold root
		oracle = []
		non_null_concepts = []

		for p in range(n):
			if label2concept(predictions[p*p]) != "NULL":
				non_null_concepts.append((p, label2concept(predictions[p*p])))

		if len(non_null_concepts) == 0:
			return -1

		for i in range(len(non_null_concepts)):
			p, current_concept = non_null_concepts[i]
			t = (-1, p, "ROOT", current_concept)
			if sentence.id in gold_relation_dict and t in gold_relation_dict[sentence.id]:
				oracle = [i]
				break

		#Make examples
		examples = [self.make_root_example(sentence, k[0], predictions) for k in non_null_concepts]
		condition_list = [(k*k+1,'a')for k in range(n)]

		pred = self.sch.predict(examples=examples,
								my_tag=n*n+n+5,
								oracle=oracle,
								condition=condition_list,
								learner_id=3)

		r = non_null_concepts[pred][0]
		#remove all the incoming relations that were predicted into the rooot
		for i in range((r*r)+(r)+1, (r*r)+(r)+(r+1)):
			predictions[i] = edgeLabels["NOEDGE"]
		return r 

	def _run(self, sentence):

		#global training_id_dict
		global flag
		global seen_dict
		global example_cache
		global prev_sent_id
		global edgeLabels

		if sentence.id != prev_sent_id:
			prev_sent_id = sentence.id
			example_cache = {}

		num_not_null = 0
		for i in range(len(sentence.spans)):
			if sentence.spans[i].concept != "NULL":
				num_not_null += 1

		if len(sentence.spans) > 10 and flag:
		#if (num_not_null > 10 or len(sentence.spans) > 25) and flag:
			return [], []
			#sentence.spans = sentence.spans[:10]
			#n = 10
		else:
			n = len(sentence.spans)
		try:
			pass
			if sentence.id not in seen_dict and flag:
				#print num_not_null, len(sentence.spans), training_id_dict[sentence.id], sentence.id
				seen_dict[sentence.id] = 1
		except KeyError:
			pass

		graph = nx.MultiDiGraph()
		predictions = [None]*(n*n)
		node_expansions = [edgeLabels["NOEDGE"]]*n


		for k in xrange(n):
			#predictions[k*k] = concept2label(sentence.spans[k].concept)
			self.predict_concept(sentence, k, k*k, predictions)
			graph.add_node(k)
			#Do we need to split the concept further
			predicted_concept_split = label2concept(predictions[k*k]).split('_')

			if len(predicted_concept_split) == 2:
				self.predict_relation_exp(sentence, k, node_expansions, predictions)


		root_index = self.predict_root(sentence, predictions)
		i = 0
		for k in xrange(n):
			#self.predict_concept(sentence, k, i, predictions)
			#Do we need to split the concept further
			#predicted_concept_split = label2concept(predictions[i]).split('_')
			#if len(predicted_concept_split) == 2:
			#	self.predict_relation_exp(sentence, k, node_expansions, predictions)

			i += 1
			for j in xrange(k):
				if j!= root_index:
					self.predict_relation(sentence, k, j, i, predictions)
				else:
					predictions[i] = edgeLabels["NOEDGE"]

				if predictions[i] != edgeLabels["NOEDGE"]:
					graph.add_edge(k,j)
				i += 1
			if k == root_index:
				for j in xrange(k):
					predictions[i] = edgeLabels["NOEDGE"]
					i+=1
			else:
				for j in xrange(k):
					self.predict_relation(sentence, j, k, i, predictions)
					if predictions[i] != edgeLabels["NOEDGE"]:
						graph.add_edge(j,k)
					i += 1

		if not flag:
			a  = nx.simple_cycles(graph)
			b = [x for x in a]
			#if b != []:
				#print sentence.id
				#print [label2concept(predictions[c*c]) for c in b[0]]




		return predictions, node_expansions, root_index

	def predictOneBest(self, sentence):
		#print [span.words for span in sentence]
		output = []
		for i in xrange(len(sentence)):
			span = sentence.spans[i]
			#print span.words
			k_best_concepts = get_K_best_concepts(sentence.spans[i], self.span_concept_dict, self.vnpb_words_concepts_dict)
			pred = 0
			output.append(concept2label(k_best_concepts[pred][0]))
		return output

def main(argv):
	if len(argv) < -1:
		print "usage python concept_relation_joint_learning.py concept_training_dataset_p concept_test_dataset_p span_concept_dict_p vnpb_words_concepts_dict_p relation_train_dataset_p relation_test_dataset_p kbest_dep_parse_p original_amr_aligned nodes_relation_dict_p"
		return

	global edgeLabelsList
	global span_concept_dict_p
	global vnpb_words_concepts_dict_p
	global dep_parse
	global gold_relation_dict
	global concept_labels
	global concept_map
	global relation_map
	global training_id_dict
	global flag
	global seen_dict
	global prev_sent_id
	global nodes_relation_dict_in
	global nodes_relation_dict_out
	global nodes_relation_dict_pair
	global dep_parse_nx

	#change this is you want to use debugger
	debug = False

	if debug:
		concept_training_dataset_p = "../data/amr-release-1.0-training-proxy/concept_dataset.p"
		concept_test_dataset_p = "../data/amr-release-1.0-test-proxy/concept_dataset.p"
		span_concept_dict_p = "../data/amr-release-1.0-training-proxy/span_concept_dict.p"
		vnpb_words_concepts_dict_p = "../data/amr-release-1.0-training-proxy/vnpb_words_concepts_dict.p"
		relation_training_dataset_p = "../data/amr-release-1.0-training-proxy/relation_dataset.p"
		relation_test_dataset_p = "../data/amr-release-1.0-test-proxy/relation_dataset.p"
		kbest_dep_parse_p_train = "../data/amr-release-1.0-training-proxy/dep_parse.p"
		kbest_dep_parse_p_test = "../data/amr-release-1.0-test-proxy/dep_parse.p"
		original_amr_aligned = "../data/amr-release-1.0-test-proxy/amr-release-1.0-test-proxy.aligned"
		nodes_relation_dict_p = "../data/amr-release-1.0-training-proxy/nodes_relation_dict.p"
		amr_out_file_name = "proxy-out-temp_quant_d"
		amr_in_file_name = "proxy_in-temp_quant_d"

	else:
		concept_training_dataset_p = argv[0]
		concept_test_dataset_p = argv[1]
		span_concept_dict_p = argv[2]
		vnpb_words_concepts_dict_p = argv[3]
		relation_training_dataset_p = argv[4]
		relation_test_dataset_p = argv[5]
		kbest_dep_parse_p_train = argv[6]
		kbest_dep_parse_p_test = argv[7]
		original_amr_aligned = argv[8]
		nodes_relation_dict_p = argv[9]
		amr_out_file_name = argv[10]
		amr_in_file_name = argv[11]

	print "Starting Up!"
	nodes_relation_dict_out, nodes_relation_dict_in, nodes_relation_dict_pair = pickle.load(open(nodes_relation_dict_p))

	#Format of concept_training_dataset
	#concept_training_dataset = {id: [span, pos, concept]}
	#concept_training_dataset = pickle.load(open("data/amr-release-1.0-training-proxy/concept_training_dataset_p", "rb"))

	#Read original amr
	amr_dict = read_amr(open(original_amr_aligned))
	#print len(amr_dict)

	#Prepare training data
	concept_training_dataset = pickle.load(open(concept_training_dataset_p, "rb"))
	gold_relation_dict = pickle.load(open(relation_training_dataset_p, "rb"))
	dep_parse = pickle.load(open(kbest_dep_parse_p_train, "rb"))

	dep_parse_nx = {}
	for each_id in dep_parse:
		each_dp = dep_parse[each_id]
		dep_parse_graph_u = nx.Graph()
		dep_parse_graph_d = nx.DiGraph()
		for each_src in each_dp:
			for each_tgt in each_dp[each_src]:
				dep_parse_graph_u.add_edge(each_src, each_tgt[0], {'label': each_tgt[1]})
				dep_parse_graph_d.add_edge(each_src, each_tgt[0], {'label': each_tgt[1]})

		dep_parse_nx[each_id] = (dep_parse_graph_u, dep_parse_graph_d)


	training_id_dict = {}
	count = 0
	subcount = 0
	lens = []
	training_sentences = []
	for id, concept_training_data in concept_training_dataset.iteritems():
		current_spans = []
		training_id_dict[id] = count
		i = 0
		for span_index, [span, pos, concept, name, ner] in enumerate(concept_training_data):
			num_words = len(span.split())
			current_spans.append(Span(span, pos, range(i, i+num_words), ner, concept))
			i += num_words
		training_sentence = Sentence(id, current_spans)
		lens.append(len(training_sentence.spans))
		count += 1
		if len(training_sentence.spans) <= 10:
			subcount += 1

		training_sentences.append(training_sentence)
	#print subcount, count
	#print sorted(lens, reverse=True)[:100]

	amr_out_file = open(amr_out_file_name, 'w')
	amr_in_file = open(amr_in_file_name, 'w')

	#Prepare vw parameters
	N = len(training_sentences)
	#N = 1
	#N = 10
	vw = pyvw.vw("--search 0 --csoaa_ldf m --quiet --search_task hook --ring_size 2048 --search_no_caching -q a: ")
	task = vw.init_search_task(ConceptRelationLearning)
	prev_sent_id = training_sentences[0].id

	#Start training
	print "Learning.."
	start_time = time.time()
	for p in range(1):
		seen_dict = {}
		task.learn(training_sentences[:])

	print "Time taken: " + str(time.time() - start_time)

	flag = False
	#Prepare test data
	concept_test_dataset = pickle.load(open(concept_test_dataset_p, "rb"))
	test_gold_relation_dict = pickle.load(open(relation_test_dataset_p, "rb"))
	dep_parse = pickle.load(open(kbest_dep_parse_p_test, "rb"))

	dep_parse_nx = {}
	for each_id in dep_parse:
		each_dp = dep_parse[each_id]
		dep_parse_graph_u = nx.Graph()
		dep_parse_graph_d = nx.DiGraph()
		for each_src in each_dp:
			for each_tgt in each_dp[each_src]:
				dep_parse_graph_u.add_edge(each_src, each_tgt[0], {'label': each_tgt[1]})
				dep_parse_graph_d.add_edge(each_src, each_tgt[0], {'label': each_tgt[1]})

		dep_parse_nx[each_id] = (dep_parse_graph_u, dep_parse_graph_d)

	gold_relation_dict = {}
	test_sentences = []
	for id, concept_test_data in concept_test_dataset.iteritems():
		current_spans = []
		i = 0
		for span_index, [span, pos, concept, name, ner] in enumerate(concept_test_data):
			num_words = len(span.split())
			current_spans.append(Span(span, pos, range(i, i+num_words), ner, concept))
			#print current_spans[-1].word_positions
			i += num_words
		test_sentence = Sentence(id, current_spans)
		test_sentences.append(test_sentence)

	#test_sentences = test_sentences[:10]
	#Start testing
	start_time = time.time()
	print "Testing.."

	#print len(test_sentences)
	predictions = []
	t2 = []
	i = 0
	for test_sentence in test_sentences:
		id = test_sentence.id
		#print id
		predicted, node_exp, root_index = task.predict(eraseAnnotations(test_sentence))
		predictions.append(predicted)
		t2.append(test_sentence)
		amr_in_file.write(amr_dict[id])
		amr_in_file.write('\n')
		write_amr_to_file(test_sentence.id, predicted, node_exp, concept_map, relation_map, amr_out_file,
								nodes_relation_dict_out, nodes_relation_dict_in, nodes_relation_dict_pair, root_index)
		predictions[i] = predicted
		i+=1

	evaluate_concepts(t2, predictions, concept_map)
	evaluate_concepts_true(t2, predictions, concept_map, original_amr_aligned)
	print "Time taken: " + str(time.time() - start_time)
	amr_in_file.close()
	amr_out_file.close()


if __name__ == "__main__":
	main(sys.argv[1:])
