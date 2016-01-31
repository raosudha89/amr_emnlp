#!/bin/sh

#TR_FOLDER="../data/train"
TR_FOLDER="../data/deft-p2-amr-r1-amrs-training-bolt"
test="CLIPUMD"
TE_FOLDER="../data/$test"
TE_ALIGNED="$test.aligned"
python concept_relation_joint_learning_on_test.py \
	$TR_FOLDER/concept_dataset.p \
	$TE_FOLDER/concept_dataset.p \
	$TR_FOLDER/span_concept_dict.p \
	$TR_FOLDER/vnpb_words_concepts_dict.p \
    	$TR_FOLDER/relation_dataset.p \
	$TR_FOLDER/dep_parse.p \
	$TE_FOLDER/dep_parse.p \
	$TE_FOLDER/$TE_ALIGNED \
	$TR_FOLDER/nodes_relation_dict.p \
	../output/$test.out-tem \

echo
echo

sed 's/\/ \//\//g' ../output/$test.out-tem > ../output/$test.out
rm ../output/$test.out-tem
#python smatch_code/smatch.py -f ../output/$test.out ../output/$test.in --pr
