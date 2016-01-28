Dependencies - Python 2.7, NLTK, SciPy, networkx, Vowpal Wabbit
Optional dependencies (Required if running on other dataset) - Stanford Tagger, Parser, NER

Parser should run on your favorite *nix variant, but has only been exhaustively tested on MacOSX so far.

#################################################################################################

To directly run the parser on the Little Prince dataset (provided with the code),

	1) Download vowpal wabbit and install it (https://github.com/JohnLangford/vowpal_wabbit)
	2) Set the environment variable VW_PYTHON_PATH to the absolute location of the python interface to VW (Found in VW_HOME/python)
	3) 'sh scripts/run_joint_learning_test.sh'
	4) Wait :) The parser can take anywhere from 6 to 15 minutes depending on the machine configuration for this dataset (and more for others!).
	5) Output will be found in the output/ folder
################################################################################################

To run the parser on any other dataset (train + test files):

	1) Download the Stanford POS Tagger, NER and Parser and set the path to these in scripts/config.sh and source the config script by running
	'. scripts/config.sh'. Replace the lexparser.sh in the Parser folder by the one provided with this code.

	2) Run the JAMR aligner on the train and test files (https://github.com/jflanigan/jamr), and place the output of these in two different 
	folders in the data/ folder. Ensure that these files have .aligned suffix, and the folders have the same name as the files. For eg if your 
	training file was called amr.txt, the aligned file should be called amr.aligned, and be placed in data/amr/. Refer to the files in 
	data/amr-release-1.0-training-lp and data/amr-release-1.0-test-lp

	3) Run the common preprocessing script from the scripts folder for both the training and test set
		'cd scripts; sh preprocess.sh ../data/<amr-folder>/<aligned-amr>'

	4) Run the training preprocessing script on the training set
		'cd scripts; sh preprocess_training_dataset.sh ../data/<train-amr-folder>/<aligned-amr>'

	5) Run the test preprocessing script on the test set
		'cd scripts; sh preprocess_test_dataset.sh ../data/<test-amr-folder>/<aligned-amr>'

	6) Set the file paths in scripts/run_joint_learning_test.sh and run the parser
		'cd scripts; sh run_joint_learning_test.sh'

	7) Read points 4 and 5 from previous section.

################################################################################################
	
