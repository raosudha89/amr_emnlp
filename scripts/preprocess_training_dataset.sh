#!/bin/sh
# Usage preprocess_training_dataset <amr_aligned_file>

amr_name="$(basename "$1")"
amr_name="${amr_name%.*}"

echo Creating graph structure...
#Create Networkx graph structure from amr aligned file. This will create the amr_nx_graphs.p file.
python amr_reader.py ../data/$amr_name/$amr_name.aligned > ../data/$amr_name/amr_nx_graphs 
mv amr_nx_graphs.p ../data/$amr_name/
echo Done!
echo

echo Aggregating metadata...
#Aggregate all metadata for amr sentences. This will create the amr_aggregated_metadata.p file.
python aggregate_sentence_metadata.py  ../data/$amr_name/$amr_name.aligned ../data/$amr_name/$amr_name.sentences ../data/$amr_name/$amr_name.pos ../data/$amr_name/$amr_name.ner ../data/$amr_name/$amr_name.parse
mv amr_aggregated_metadata.p ../data/$amr_name/
mv dep_parse.p dep_parse ../data/$amr_name/
echo Done!
echo 

echo Creating concept training dataset...
#Create concept training datatset i.e. create concept_dataset.p
python create_concept_dataset.py ../data/$amr_name/amr_nx_graphs.p ../data/$amr_name/amr_aggregated_metadata.p > ../data/$amr_name/concept_dataset
mv concept_dataset.p ../data/$amr_name/
echo Done!
echo

echo Creating span-concept dictionary...
#For each span, get a list of all concepts (with their counts). This creates the span_concept_dict.p file.
python create_span_concept_dict.py ../data/$amr_name/concept_dataset.p ../data/$amr_name > ../data/$amr_name/span_concept_dict
mv span_concept_dict.p ../data/$amr_name/
echo Done!
echo 

echo Using verbnet...
#
python read_vnpbMappings.py ../1.2.2c/vn-pb/vnpbMappings ../data/$amr_name > ../data/$amr_name/vnpb_words_concepts_dict
echo Done!
echo

echo Creating relation learning dataset
#
python create_relation_dataset.py ../data/$amr_name/amr_nx_graphs.p ../data/$amr_name/concept_dataset.p 1 > ../data/$amr_name/relation_dataset
mv relation_dataset.p nodes_relation_dict.p ../data/$amr_name/
echo Done!
echo

