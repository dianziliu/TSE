import os
import pickle
import sys
from os.path import join
from textwrap import shorten

import numpy as np
# import tensorflow as tf
# from keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.sequence import pad_sequences

# from untils import build_data
from .process import build_data


class Data_Loader():
    Glove_path="glove"
    def __init__(self, flags):

        # 创建独立的文件夹来保存处理后的文件
        self.dir=flags.filename.split('.')[0]
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        self.pro_path=os.path.join(self.dir,"data")

        if not os.path.exists(self.pro_path+'.pkl'):
            build_data(flags.filename,self.pro_path)
        data = pickle.load(open(self.pro_path+'.pkl','rb'))

        # print(len(data))
        vec_texts 	= data['vec_texts']
        vocab 		= data['vocab']
        vec_uit 	= data['vec_uit']
        vec_u_text 	= data['vec_u_text']
        vec_i_text 	= data['vec_i_text']
        user2idx 	= data['user2idx']
        item2idx 	= data['item2idx']
        
        self.user2idx=user2idx
        self.item2idx=item2idx

        self.Glove_path = flags.glovepath
        self.filename 	= flags.filename
        self.word2idx 	= data['word2idx']
        self.batch_size = flags.batch_size
        self.num_user 	= len(user2idx)
        self.num_item 	= len(item2idx)
        self.vocab_size = len(vocab)+1
        self.data_size 	= len(vec_uit)
        self.emb_size 	= flags.emb_size

        # self.test_size  = flags.test_size

        self.t_num 	= 6
        self.maxlen = 60
        self.vec_texts 	= pad_sequences(vec_texts, maxlen = self.maxlen)
        # self.vec_u_text = pad_sequences(vec_u_text, maxlen = self.t_num, padding='post')
        # self.vec_i_text = pad_sequences(vec_i_text, maxlen = self.t_num, padding='post')
        self.vec_u_text = vec_u_text[:,:self.t_num]
        self.vec_i_text = vec_i_text[:,:self.t_num]

        self.vec_uit = np.array(vec_uit)

        pmtt = np.random.permutation(self.data_size)
        pmtt_file = self.pro_path+'_pmtt.npy'

        if not os.path.exists(pmtt_file):
            np.save(pmtt_file, pmtt)
        else:
            print('pmtt file exist')
            pmtt = np.load(pmtt_file).astype(np.int32)

        # self.vec_uit = np.random.permutation(self.vec_uit)

        self.vec_uit = self.vec_uit[pmtt]
        self.vec_u_text = self.vec_u_text[pmtt]
        self.vec_i_text = self.vec_i_text[pmtt]

        # print(len(self.vec_uit))
        # print(len(self.vec_u_text))

        self.train_size = int(self.data_size*(1-flags.test_size))
        # self.test_size = int(self.data_size* flags.test_size )
        # 固定测试集的大小去验证
        self.test_size = int(self.data_size* 0.1)
        
        self.train_uit = self.vec_uit[:self.train_size]
        self.train_u_text = self.vec_u_text[:self.train_size]
        self.train_i_text = self.vec_i_text[:self.train_size]
        # self.test_uit = self.vec_uit[self.train_size:]
        self.test_uit = self.vec_uit[-self.test_size:]
        self.test_u_text = self.vec_u_text[-self.test_size:]
        self.test_i_text = self.vec_i_text[-self.test_size:]

        self.pointer = 0

        self.get_embedding()
    def next_batch(self):
        begin 	= self.pointer*self.batch_size
        end		= (self.pointer+1)*self.batch_size
        self.pointer+=1
        if end >= self.train_size:
            end = self.train_size
            self.pointer = 0

        labels = self.train_uit[begin:end][:,3:]
        users = self.train_uit[begin:end][:,0]
        items = self.train_uit[begin:end][:,1]
        texts = self.train_uit[begin:end][:,2]

        utexts = self.train_u_text[begin:end]
        itexts = self.train_i_text[begin:end]
        # print(i_texts)
        return users, items, labels, utexts,itexts, texts


    def all_train_data(self):
        labels = self.train_uit[:,3:]
        users  = self.train_uit[:,0]
        items  = self.train_uit[:,1]
        texts  = self.train_uit[:,2]

        utexts = self.train_u_text
        itexts = self.train_i_text
        # print(i_texts)
        return users, items, labels, utexts,itexts, texts
        
    def eval(self):
        labels = self.test_uit[:,3:]
        users  = self.test_uit[:,0]
        items  = self.test_uit[:,1]
        texts  = self.test_uit[:,2]

        utexts = self.test_u_text
        itexts = self.test_i_text


        return users, items, labels, utexts, itexts, texts

    def assert_doc(self, idxs, rating):
        res = []
        for idx in idxs:
            # label = self.vec_uit[self.vec_uit[:,2] == doc_idx][0][3]
            utexts = self.train_u_text[idx]
            itexts = self.train_i_text[idx]
            u_flag = 0
            for utext in utexts:
                if utext == 0:
                    continue
                label = self.vec_uit[self.vec_uit[:,2] == utext][0][3]
                if label == rating:
                    u_flag +=1
            i_flag = 0
            for itext in itexts:
                if itext == 0:
                    continue
                label = self.vec_uit[self.vec_uit[:,2] == itext][0][3]
                if label == rating:
                    i_flag +=1
            if u_flag >1 and i_flag > 1:
                res.append(idx)
        return res

    def assert_docs(self, pos_idxs, neg_idxs):
        pos = []
        neg = []
        pos = self.assert_doc(pos_idxs, 5)
        neg = self.assert_doc(neg_idxs, 1)
        if len(pos)!=0 and len(neg)!=0:
            print(len(pos), len(neg))
        if len(pos) == 0 or len(neg) == 0:
            return False
        else:
            return pos[0], neg[0]





    def find_a_user(self):
        # while True:
        #     idx  = np.random.randint(self.train_size)
        all_users=list(range(self.train_size))
        # np.random.shuffle(all_users)

        for idx in all_users:
            user = self.train_uit[idx][0]
            sub_indices = np.where(self.train_uit[:,0] == user)[0]

            pos_indices = np.where(self.train_uit[sub_indices,3] == 5)[0]
            neg_indices = np.where(self.train_uit[sub_indices,3] == 1)[0]

            if len(pos_indices) == 0 or len(neg_indices) == 0:
                pass
            else:
                pos_idxs = sub_indices[pos_indices]
                neg_idxs = sub_indices[neg_indices]

                res = self.assert_docs(pos_idxs, neg_idxs)
                if res == False:
                    continue
                else:
                    pos_idx, neg_idx = res

                # pos_idx = np.random.choice(pos_idxs)
                # neg_idx = np.random.choice(neg_idxs)

                pos = self.train_uit[pos_idx]
                neg = self.train_uit[neg_idx]

                uit = np.array([pos,neg])
                idx = np.array([pos_idx, neg_idx])

                break


        user  = uit[:,0]
        item  = uit[:,1]
        text  = uit[:,2]
        label = uit[:,3:]

        print(uit.shape)


        utexts = self.train_u_text[idx]
        itexts = self.train_i_text[idx]



        for utext in utexts[1]:
            # print(utexts)
            if utext == 0:
                continue
            # print(np.where(self.vec_uit[:,2] == utext))
            ulabel = self.vec_uit[self.vec_uit[:,2] == utext][0][3]
            print("utext label: ", ulabel)
        for itext in itexts[1]:
            if itext == 0:
                continue
            ilabel = self.vec_uit[self.vec_uit[:,2] == itext][0][3]
            print('itext label: ', ilabel)


        return user,item,label,utexts,itexts,text






    def sample_point(self):
        # seed = np.random.random()
        seed = 0.6
        index = []
        for i in range(self.train_size):
            if seed<0.5 and self.train_uit[i][3]==5:
                index.append(i)
            elif seed>0.5 and self.train_uit[i][3]==1:
                index.append(i)
        idx = np.random.choice(index)

        # idx = np.random.randint(self.train_size)
        print('random index: ', idx)

        sample_data = self.train_uit[idx:idx+1]

        user  = sample_data[:,0]
        item  = sample_data[:,1]
        text  = sample_data[:,2]
        label = sample_data[:,3:]

        utexts = self.train_u_text[idx:idx+1]
        itexts = self.train_i_text[idx:idx+1]

        # print(text)
        # print(utexts, itexts)





        return user,item, label, utexts, itexts, text

    def reset_pointer(self):
        self.pointer = 0

    def get_embedding(self):
        # emb_file = self.filename.split('.')[0]+'_'+str(self.emb_size)+'d.emb'
        emb_file=self.pro_path+'d.emb'
        if not os.path.exists(emb_file):
            self.w_embed = np.random.uniform(-0.25,0.25,(self.vocab_size, self.emb_size))
            self.w_embed[0] = 0
            file = os.path.join(self.Glove_path,'glove.6B.'+str(self.emb_size)+'d.txt')
            fr = open(file)
            for line in fr.readlines():
                line = line.strip()
                listfromline = line.split()
                word = listfromline[0]
                if word in self.word2idx:
                    vect = np.array(list(map(np.float32,listfromline[1:])))
                    idx = self.word2idx[word]
                    self.w_embed[idx] = vect
            np.savetxt(emb_file, self.w_embed, fmt='%.8f')
        else:
            self.w_embed = np.genfromtxt(emb_file)


    def validate(self):
        total = self.data_size//self.batch_size
        rand = np.random.randint(total)
        for i in range(rand):
            self.next_batch()
        u,i,l,uts,its,t = self.next_batch()
        print(t,l)
        widxs = self.vec_texts[t]
        idx2word = {v[1]:v[0] for v in self.word2idx.items()}
        
        for widx in widxs:
            words = [idx2word[idx] for idx in widx if idx!=0]
            print(' '.join(words))
            print('\n\n')



if __name__ == '__main__':
    prefix = 'amazon_data'
    filename = os.path.join(prefix,'Musical_Instruments_5.json')


    flags = tf.flags.FLAGS 	
    tf.flags.DEFINE_string('filename',filename,'name of file')
    tf.flags.DEFINE_integer('batch_size',4,'batch size')
    tf.flags.DEFINE_integer('emb_size',100, 'embedding size')
    tf.flags.DEFINE_string('glovepath',"glove"," path of glove")
    # tf.flags.DEFINE_string('base_model', 'att_cnn', 'base model')
    flags(sys.argv)

    data_loader = Data_Loader(flags)

    # data_loader.sample_point()
    # data_loader.next_batch()
    # data_loader.validate()
    # data_loader.eval()
    res = data_loader.find_a_user()
    print(res)
