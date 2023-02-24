import json
import os
import pickle
import sys

import nltk
import numpy as np
# import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer

# from untils import clean_str
from .utils import clean_str

nltk.data.path.append("./nltk_data")

stopwords = nltk.corpus.stopwords.words('english')

def readfile(filename):
	f = open(filename, encoding='utf-8')
	data = []
	for line in f.readlines():
		line = json.loads(line)
		data.append(line)
	f.close()
	return data

def filter_ui(data, u_min, i_min):
	u_dict = {}
	i_dict = {}
	for line in data:
		user = line['reviewerID']
		item = line['asin']
		if user not in u_dict:
			u_dict[user] = [item]
		else:
			u_dict[user].append(item)
		if item not in i_dict:
			i_dict[item] = [user]
		else:
			i_dict[item].append(user)


	flag = 0
	while flag == 0:
		flag = 1
		for user in u_dict.keys():
			if len(u_dict[user]) < u_min:
				for item in u_dict[user]:
					i_dict[item].remove(user)
				u_dict.pop(user)
				flag = 0
		for item in i_dict.keys():
			if len(i_dict[item]) < i_min:
				for user in i_dict[item]:
					u_dict[user].remove(item)
				i_dict.pop(item)
				flag = 0
	return u_dict,i_dict


def data_after_filter(data, u_dict, i_dict):
	new_data = []
	for line in data:
		if line['asin'] in i_dict and line['reviewerID'] in u_dict:
			new_data.append(line)
	return new_data


def get_helpful_score(scores):
	fz=scores[0]
	fm=scores[1]
	if fm==0:
		return 0
	else:
		return fz/fm

def build_ui_vocab(data):
	ut_dict = {}
	u_dict = {}
	u_list = []

	it_dict = {}
	i_dict = {}
	i_list = []
	for i,line in enumerate(data):
		user = line['reviewerID']
		item = line['asin']
		idx = i+1


		if user not in u_dict:
			u_dict[user] = [idx]
		else:u_dict[user].append(idx)

		if item not in i_dict:
			i_dict[item] = [idx]
		else:i_dict[item].append(idx)
	user2idx = {user:i for i,user in enumerate(u_dict.keys())}
	idx2user = {i:user for i,user in enumerate(u_dict.keys())}
	item2idx = {item:i for i,item in enumerate(i_dict.keys())}
	idx2item = {i:item for i,item in enumerate(i_dict.keys())}
	vec_u_text = vectorize_ui_text(idx2user, u_dict)
	vec_i_text = vectorize_ui_text(idx2item, i_dict)

	vec_uit = []
	for i,line in enumerate(data):
		user = line['reviewerID']
		item = line['asin']
		rate = int(line['overall'])
		# 2021.11.1 新增
		helpful=get_helpful_score(line['helpful'])
		text_idx = i+1
		user_idx = user2idx[user]
		item_idx = item2idx[item]

		vec_uit.append([user_idx, item_idx, text_idx, rate,helpful])
	return vec_uit, vec_u_text, vec_i_text, user2idx, item2idx

def vectorize_ui_text(idx2ui, ui_dict):
	vec_ui_text = []
	for idx in range(len(ui_dict)):
		ui = idx2ui[idx]
		text_idx = ui_dict[ui]
		vec_ui_text.append(np.random.permutation(text_idx))
	return vec_ui_text


def build_vocab(data):
	texts = []
	# u_texts = {}
	# i_texts = {}
	
	for line in data:
		text = line['reviewText'] +' ' + line['summary']
		text = clean_str(text.lower())
		texts.append(text)
		
	vocab = get_vocab_freq(texts)
	# vocab = get_vocab_tfidf(texts)

	word2idx = {word:i+1 for i,word in enumerate(vocab)}
	idx2word = {i+1:word for i,word in enumerate(vocab)}

	vec_texts = vectorize_review(word2idx, texts)

	lens = [len(text) for text in vec_texts]
	print(max(lens), min(lens), np.mean(lens))

	# print(vocab)
	return vec_texts, vocab, word2idx



def vectorize_review(word2idx, texts):
	vec_texts = [[0]]

	for text in texts:
		tokens = nltk.word_tokenize(text)
		vec_text = [word2idx[token] for token in tokens  if token in word2idx]
		vec_texts.append(vec_text)
	return vec_texts

def get_vocab_freq(corpus, vocab_size=20000):
	freq_dict = {}
	for text in corpus:
		tokens = nltk.word_tokenize(text)
		for token in tokens:
			freq_dict[token] = freq_dict.get(token, 0)+1
	tuples = [[v[1],v[0]] for v in freq_dict.items()]
	tuples = sorted(tuples)[::-1]
	vocab = []
	for tp in tuples:
		word = tp[1]
		if word not in stopwords:
			vocab.append(word)
			if len(vocab)>20000:
				break
	return vocab



def get_vocab_tfidf(corpus, vocab_size = 20000):
	
	tfidf_model = TfidfVectorizer().fit(corpus)
	sparse_result = tfidf_model.transform(corpus)
	mat = np.array(sparse_result.todense())
	print(mat.shape)
	vec = np.max(mat, axis=0)
	print(vec.shape)
	index = np.argsort(vec)[::-1]
	vocab = []
	# total_vocab_size = min(vocab_size, len(tfidf_model.vocabulary_.keys()))
	idx2word = {v:k for k,v in tfidf_model.vocabulary_.items()}

	for idx in index:
		word = idx2word[idx]
		if word not in stopwords:
			vocab.append(word)
			if len(vocab)>vocab_size:
				break
	return vocab


def validate(filename):
	filename = 'Grocery_and_Gourmet_Food_5.json'
	prefix = '/home/wenjh/aHIGAN/Grocery_and_Gourmet_Food/'
	data1 = readfile(filename)
	data2 = pickle.load(open(filename.split('.')[0]+'.pkl','rb'))


	length = len(data2['vec_uit'])
	sample = np.random.randint(length)
	uit = data2['vec_uit'][sample]
	print(uit)
	user_idx = uit[0]
	item_idx = uit[1]
	text_idx = uit[2]

	user2idx = data2['user2idx']
	item2idx = data2['item2idx']
	idx2user = {v[1]:v[0] for v in user2idx.items()}
	idx2item = {v[1]:v[0] for v in item2idx.items()}

	user = idx2user[user_idx]
	item = idx2item[item_idx]

	text = data1[text_idx-1]
	print(user, text['reviewerID'])
	print(item, text['asin'])

	u_text = data2['vec_u_text'][user_idx]
	i_text = data2['vec_i_text'][item_idx]

	print(u_text, i_text)

	for text_idx in u_text:
		text = data1[text_idx-1]
		print(text['reviewerID'])
	print(u_text)


def get_neighbors(mat):
	rows, cols = mat.shape
	res_mat = np.zeros((rows,rows))
	for i in range(rows):
		sys.stdout.write('\r {}/{}'.format(i,rows))
		a1 = mat[i]
		for j in range(i,rows):
			a2 = mat[j]


			commo_vec = (a1*a2!=0).astype(int)
			equal_vec = (a1==a2).astype(int)

			coeq_vote = np.sum(commo_vec*equal_vec)
			comm_vote = np.sum(commo_vec)
			norm = np.sqrt(comm_vote)
			norm = max(norm,1)
			res = coeq_vote/norm

			res_mat[i,j] = res 
			res_mat[j,i] = res
	return res_mat

def get_neighbors_1(mat):
	rows,cols = mat.shape
	res_mat = np.zeros((rows,rows))

	for i in range(rows):
		sys.stdout.write('\r {}/{}'.format(i,rows))
		a1 = mat[i]
		nz_idx = np.where(a1!=0)[0]
		a1 = a1[nz_idx]
		sub_mat = mat[i:].T[nz_idx].T

		commo_vec = (a1*sub_mat!=0).astype(int)
		equal_vec = (a1==sub_mat).astype(int)

		coeq_vote = np.sum(commo_vec*equal_vec, axis=1)
		comm_vote = np.sum(commo_vec, axis=1)

		norm = np.sqrt(comm_vote)
		norm = np.maximum(norm, 1)
		res = coeq_vote/norm 

		res_mat[i,i:] = res 
		res_mat[i:,i] = res 
	return res_mat


def build_ui_text(vec_uit, num_user, num_item, dst_Dir):
	# filename = filename.split('.')[0]
	ui_mat = np.zeros((num_user, num_item))
	pmtt_file = dst_Dir+'_pmtt.npy'
	if os.path.exists(pmtt_file):
		pmtt = np.load(pmtt_file)
	else:
		pmtt = np.random.permutation(len(vec_uit))

	train_size = int(len(vec_uit)*0.8)
	train_vec_uit = np.array(vec_uit)[pmtt][:train_size]
	for uit in train_vec_uit:
		u = uit[0]
		i = uit[1]
		r = uit[3]
		ui_mat[u,i] = r 
	u_neighbor_mat = np.zeros((num_user, num_user))
	file = dst_Dir+'_u_neighbors.npy'
	if not os.path.exists(file):
		print('user neighbors file not exists')
		u_neighbor_mat = get_neighbors_1(ui_mat)
		np.save(file, u_neighbor_mat)
	else:
		u_neighbor_mat = np.load(file)
	file = dst_Dir+'_i_neighbors.npy'
	if not os.path.exists(file):
		print('item neighbors file not exists')
		i_neighbor_mat = get_neighbors_1(ui_mat.T)
		np.save(file, i_neighbor_mat)
	else:
		i_neighbor_mat = np.load(file)

	print("getting documents...")
	vec_u_text = get_doc_neighbors(vec_uit, u_neighbor_mat, i_neighbor_mat, 'item')
	vec_i_text = get_doc_neighbors(vec_uit, u_neighbor_mat, i_neighbor_mat, 'user')
	np.savetxt(dst_Dir+'_utexts.txt', vec_u_text, fmt='%d')
	np.savetxt(dst_Dir+'_itexts.txt', vec_i_text, fmt='%d')
	return vec_u_text, vec_i_text


def get_doc_neighbors(vec_uit, u_neighbor_mat, i_neighbor_mat, name='item'):
	uit = np.array(vec_uit)
	u_dat = uit[:,0]
	i_dat = uit[:,1]
	d_dat = uit[:,2]
	y_dat = uit[:,3]
	num = 10

	data1 = i_dat if name == 'item' else u_dat
	data2 = u_dat if name == 'item' else i_dat
	neighbor_mat = u_neighbor_mat if name == 'item' else i_neighbor_mat
	res = []
	length = len(uit)
	for i in range(length):
		label = y_dat[i]
		item = data1[i]
		index = np.where(data1==item)[0]

		# labels = y_dat[index]

		# index = index[labels == label]

		# index = np.where(y_dat == label)[0]

		user = data2[i]
		users = data2[index]

		sims = neighbor_mat[user]
		similarity = sims[users]

		sort_index = np.argsort(similarity)[::-1]

		addition = max(num-len(index), 0)

		selection = len(index) if num>len(index) else num

		neighbors_1 = np.concatenate([index[sort_index][:selection]+1, [0]*addition])
		neighbors_1[0] = 0
		neighbors_1 = np.random.permutation(neighbors_1)

		# if len(index)-1>=num:
		# 	neighbors_1 = index[sort_index][1:num+1]+1
		# else:
		# 	neighbors_1 = np.concatenate([index[sort_index][1:]+1,np.array([i+1]*(num-len(index)+1))])

		res.append(neighbors_1)

	return np.array(res)


def build_data(filename,dst_Dir):
	data = readfile(filename)

	# 临时文件 
	temp_file=dst_Dir+'_temp.pkl'
	print('building vocab...')
	if not os.path.exists(temp_file):
		vec_texts, vocab, word2idx = build_vocab(data)
		temp_data = {}
		temp_data['text'] = vec_texts
		temp_data['vocab'] = vocab
		temp_data['word2idx'] = word2idx
		fr = open(temp_file,'wb')
		pickle.dump(temp_data, fr)
		fr.close()
	else:
		fr = open(temp_file,'rb')
		temp_data = pickle.load(fr)
		vec_texts = temp_data['text']
		vocab = temp_data['vocab']
		word2idx = temp_data['word2idx']

	print('building ui vocab...')
	vec_uit, vec_u_text, vec_i_text, user2idx, item2idx = build_ui_vocab(data)
	num_user = len(user2idx)
	num_item = len(item2idx)

	print('building ui similar text...')
	vec_u_text, vec_i_text = build_ui_text(vec_uit, num_user, num_item, dst_Dir)

	data_save = {}
	data_save['vec_texts'] 	= vec_texts
	data_save['vocab'] 		= vocab
	data_save['word2idx'] 	= word2idx
	data_save['vec_uit'] 	= vec_uit
	data_save['vec_u_text'] = vec_u_text
	data_save['vec_i_text'] = vec_i_text
	data_save['user2idx'] 	= user2idx
	data_save['item2idx'] 	= item2idx

	print('writing back...')
	fr = open(dst_Dir+'.pkl','wb')
	pickle.dump(data_save,fr)
	fr.close()


if __name__ == '__main__':
	prefix = '/home/wenjh/aHIGAN/Grocery_and_Gourmet_Food/'
	filename = prefix+'Grocery_and_Gourmet_Food_5.json'

	build_data(filename)
	# validate(filename)
