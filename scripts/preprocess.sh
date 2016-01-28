#!/bin/sh
# Usage: sh preprocess.sh <amr_aligned_file>
# Set the path of postagger, ner and parser 

amr_name="$(basename "$1")"
amr_name="${amr_name%.*}"

echo "Extracting sentences..."
python extract_sentences_from_amr_input.py ../data/$amr_name/$amr_name.aligned ../data/$amr_name/$amr_name.sentences
echo "Done!"
echo

echo "POS-tagging sentences..."
curr_dir=$PWD
cd ${POS_TAGGER}
java -mx300m -cp 'stanford-postagger.jar:lib/*' edu.stanford.nlp.tagger.maxent.MaxentTagger -model models/wsj-0-18-left3words-distsim.tagger -tokenize false -textFile $curr_dir/../data/$amr_name/$amr_name.sentences > $curr_dir/../data/$amr_name/$amr_name.pos
echo "Done!"
echo 

echo "Doing NER..."
cd ${NER}
java -mx600m -cp 'stanford-ner.jar:lib/*' edu.stanford.nlp.ie.crf.CRFClassifier -loadClassifier classifiers/english.muc.7class.distsim.crf.ser.gz -textFile $curr_dir/../data/$amr_name/$amr_name.sentences -outputFormat inlineXML > $curr_dir/../data/$amr_name/$amr_name.ner
echo "Done!"
echo 

echo "Parsing sentences..."
cd ${PARSER}
sh lexparser.sh $curr_dir/../data/$amr_name/$amr_name.sentences > $curr_dir/../data/$amr_name/$amr_name.parse 
echo "Done!"
echo 
