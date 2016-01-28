import sys

def calculate_p_r_f1(gold_concepts, pred_concepts):
	tp = len(set(gold_concepts).intersection(pred_concepts))
	fn = len(set(gold_concepts).difference(pred_concepts))
	fp = len(set(pred_concepts).difference(gold_concepts))
	if tp+fp == 0:
		p = 0
	else:
		p = tp*1.0/(tp + fp)
	if tp+fn == 0:
		r = 0
	else:
		r = tp*1.0/(tp + fn)
	if p+r == 0:
		f1 = 0
	else:
		f1 = 2*p*r/(p + r)
	return p, r, f1

def evaluate_concepts(test_sentences, predictions, concept_map):
	P = 0
	R = 0
	F1 = 0
	P_seen = 0
	R_seen = 0
	F1_seen = 0
	P_unseen = 0
	R_unseen = 0
	F1_unseen = 0
	for i in range(len(test_sentences)):
		gold_concepts = []
		pred_concepts = []
		gold_concepts_seen = []
		pred_concepts_seen = []
		gold_concepts_unseen = []
		pred_concepts_unseen = []
		
		for j in range(len(test_sentences[i].spans)):
			gold_concept = test_sentences[i].spans[j].concept
			if gold_concept != "NULL":
				gold_concepts.append(gold_concept)
			if not concept_map.has_key(predictions[i][j*j]):
				pred_concept = "NULL"
			else:
				pred_concept = concept_map[predictions[i][j*j]]
			if pred_concept != "NULL":
				pred_concepts.append(pred_concept)
			
			if gold_concept == "NULL":
				continue
		
			if gold_concept in concept_map.values(): #seen concept
				gold_concepts_seen.append(gold_concept)
				pred_concepts_seen.append(pred_concept)
			else:			
				gold_concepts_unseen.append(gold_concept)
				pred_concepts_unseen.append(pred_concept)

		p, r, f1 = calculate_p_r_f1(gold_concepts, pred_concepts)
		P += p
		R += r
		F1 += f1

		p_seen, r_seen, f1_seen = calculate_p_r_f1(gold_concepts_seen, pred_concepts_seen)
		P_seen += p_seen
		R_seen += r_seen
		F1_seen += f1_seen

		p_unseen, r_unseen, f1_unseen = calculate_p_r_f1(gold_concepts_unseen, pred_concepts_unseen)
		P_unseen += p_unseen
		R_unseen += r_unseen
		F1_unseen += f1_unseen

	P = P/len(test_sentences)
	R = R/len(test_sentences)
	F1 = F1/len(test_sentences)
	print
	print "Evaluation against aligned concepts"

	print "& P & R & F"
	print "& %.3f & %.3f & %.3f" % (P, R, 2*P*R/(P+R))
	print "Micro avg F1 =", F1

	P_seen = P_seen/len(test_sentences)
	R_seen = R_seen/len(test_sentences)
	F1_seen = F1_seen/len(test_sentences)
	#print
	#print "Evaluation against aligned concepts (seen)"

	#print "& P & R & F"
	#print "& %.3f & %.3f & %.3f" % (P_seen, R_seen, 2*P_seen*R_seen/(P_seen+R_seen))
	#print "Micro avg F1 =", F1_seen

	P_unseen = P_unseen/len(test_sentences)
	R_unseen = R_unseen/len(test_sentences)
	F1_unseen = F1_unseen/len(test_sentences)

	#print
	#print "Evaluation against aligned concepts (unseen)"

	#print "& P & R"
	#print "& %.3f & %.3f" % (P_unseen, R_unseen)
	#f P_unseen + R_unseen != 0:
	#	print "Macro avg F1 =", 2*P_unseen*R_unseen/(P_unseen+R_unseen)
	#print "Micro avg F1 =", F1_unseen

def evaluate_concepts_true(test_sentences, predictions, concept_map, amr_aligned_file):
	amr_aligned = open(amr_aligned_file)
	line = amr_aligned.readline()
	gold_concepts_dict = {}
	while (line != ""):
		if line.startswith("# ::id"):
			id = line.split("::")[1].strip("# ::id").strip()
			gold_concepts_dict[id] = []
		if line.startswith("# ::node"):
			node_data = line.strip("# ::node").strip("\n")
			gold_concepts_dict[id].append(node_data.split()[1].strip())
		line = amr_aligned.readline()

	P = 0
	R = 0
	F1 = 0
	for i in range(len(test_sentences)):
		gold_concepts = gold_concepts_dict[test_sentences[i].id]
		pred_concepts = []
		for j in range(len(test_sentences[i].spans)):
			if not concept_map.has_key(predictions[i][j*j]):
				pred_concept = "NULL"
			else:
				pred_concept = concept_map[predictions[i][j*j]]
			if pred_concept != "NULL":
				pred_concepts.append(pred_concept)
			
		p, r, f1 = calculate_p_r_f1(gold_concepts, pred_concepts)
		P += p
		R += r
		F1 += f1

	P = P/len(test_sentences)
	R = R/len(test_sentences)
	F1 = F1/len(test_sentences)	
	#print
	#print "Evaluation against all concepts"
	
	#print "& P & R & F"
	#print "& %.3f & %.3f & %.3f" % (P, R, 2*P*R/(P+R))
	#print "Micro avg F1 =", F1

