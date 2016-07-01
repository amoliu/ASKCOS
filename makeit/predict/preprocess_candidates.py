# Import relevant packages
from __future__ import print_function
from global_config import USE_STEREOCHEMISTRY
import numpy as np
from scipy.sparse import coo_matrix
import cPickle as pickle
import rdkit.Chem as Chem
import rdkit.Chem.AllChem as AllChem
import os
import sys
from makeit.embedding.descriptors import rxn_level_descriptors
from keras.preprocessing.sequence import pad_sequences
import time

FROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

def get_candidates(n = 2, seed = None, outfile = '.', single_only = False, shuffle = False, skip = 0):
	'''
	Pull n example reactions, their candidates, and the true answer
	'''

	from pymongo import MongoClient    # mongodb plugin
	from rdkit import RDLogger
	lg = RDLogger.logger()
	lg.setLevel(4)
	client = MongoClient('mongodb://guest:guest@rmg.mit.edu/admin', 27017)
	db = client['prediction']
	examples = db['candidates']

	# Define generator
	class Randomizer():
		def __init__(self, seed):
			self.done_ids = []
			np.random.seed(seed)
			if outfile:
				with open(os.path.join(outfile, 'preprocess_candidates_seed.txt'), 'w') as fid:
					fid.write('{}'.format(seed))
		def get_rand(self):
			'''Random WITHOUT replacement'''
			while True:
				try:
					doc = examples.find({'found': True, \
						'random': { '$gte': np.random.random()}}).sort('random', 1).limit(1)
					if not doc: continue
					if doc[0]['_id'] in self.done_ids: continue
					self.done_ids.append(doc[0]['_id'])
					yield doc[0]
				except KeyboardInterrupt:
					print('Terminated early')
					quit(1)
				except:
					pass

	if seed == None:
		seed = np.random.randint(10000)
	else:
		seed = int(seed)
	randomizer = Randomizer(seed)
	if shuffle:
		generator = enumerate(randomizer.get_rand())
	else:
		generator = enumerate(examples.find({'found': True}))

	# Initialize (this is not the best way to do this...)
	reaction_strings = []
	reaction_true_onehot = []
	reaction_true = []
	for i, reaction in generator:
		if i < skip: continue
		if i == skip + n: break

		candidate_products = reaction['product_smiles_candidates']
		if single_only: # reduce product list to LONGEST component (SMILES)
			candidate_products_brief = list(set(
				[max(candidates.split('.'), key=len) \
					for candidates in candidate_products] 
			))
			print('Reduced {} candidates to {}'.format(len(candidate_products), len(candidate_products_brief)))
			del candidate_products
			candidate_products = candidate_products_brief

		strings = [str(reaction['reactant_smiles']) + '>>' + str(x) \
			for x in candidate_products]
		bools = [reaction['product_smiles_true'] == x \
				for x in candidate_products]
		print('rxn. {} : {} true entries'.format(i, sum(bools)))
		if sum(bools) == 0:
			print('##### True product not found / filtered out #####')
			continue
		reaction_strings.append(
			[x for (y, x) in sorted(zip(bools, strings))]
		)
		reaction_true_onehot.append(
			[y for (y, x) in sorted(zip(bools, strings))]
		)
		reaction_true.append(str(reaction['reactant_smiles']) + '>>' + str(reaction['product_smiles_true']))

	return reaction_strings, reaction_true_onehot, reaction_true

def simple_embedding(reaction_strings, reaction_true_onehot, padUpTo = 10000):
	x = []
	y = []

	for i, candidates in enumerate(reaction_strings):
		print('processing reaction {}'.format(i))
		this_rxn = np.vstack(
		 			[rxn_level_descriptors(AllChem.ReactionFromSmarts(z)) for z in candidates]
		 		)
		coo = coo_matrix(pad_sequences(this_rxn.T, maxlen = padUpTo), dtype = np.bool)
		x.append((coo.data, coo.row, coo.col, coo.shape))

	coo = coo_matrix(pad_sequences(reaction_true_onehot, maxlen = padUpTo, dtype = np.bool))
	y = (coo.data, coo.row, coo.col, coo.shape)

	del reaction_strings 
	del reaction_true_onehot

	return x, y

if __name__ == '__main__':
	single_only = True # whether to reduce product candidates to longest product only
	n = 500
	padUpTo = 500
	shuffle = False
	skip = 500
	if len(sys.argv >= 2):
		n = int(sys.argv[1])
	if len(sys.argv >= 3):
		skip = int(sys.argv[2])

	reaction_strings, reaction_true_onehot, reaction_true = get_candidates(n = n, single_only = single_only, shuffle = shuffle, skip = skip)
	# for i, example in  enumerate(reaction_true_onehot):
		# print('rxn {}. {} true candidates'.format(i, sum(example)))
		# #print([reaction_strings[i][j] for j, o in enumerate(example) if o])
	x, y = simple_embedding(reaction_strings, reaction_true_onehot, padUpTo = padUpTo)
	# for example in x:
	# 	print(example.shape)

	rounded_time = '{}-{}'.format(skip, skip + n - 1)

	with open(os.path.join(FROOT, 'x_coo_{}{}.dat'.format(rounded_time, single_only * '_singleonly')), 'wb') as outfile:
		pickle.dump(x, outfile, pickle.HIGHEST_PROTOCOL)
	with open(os.path.join(FROOT, 'y_coo_{}{}.dat'.format(rounded_time, single_only * '_singleonly')), 'wb') as outfile:
		pickle.dump(y, outfile, pickle.HIGHEST_PROTOCOL)
	with open(os.path.join(FROOT, 'z_rxns_{}.dat'.format(rounded_time)), 'wb') as outfile:
		pickle.dump(reaction_true, outfile, pickle.HIGHEST_PROTOCOL)