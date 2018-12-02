#coding=GBK
'''
Created on 2017��4��5��

@author: Scorpio.Lu
'''
import collections
import re  
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
'''
��ȡԴ�ļ�,��תΪlist���
@param filename:�ļ���
@return: list of words
'''
def read_file(filename):
    f=open(filename,'r')
    file_read=f.read()
    words_=re.sub("[^a-zA-Z]+", " ",file_read).lower() #����ƥ��,ֻ���µ��ʣ��Ҵ�д��Сд
    words=list(words_.split())  #length of words:1121985
    return words
    
words=read_file('��������1-7Ӣ��ԭ��.txt')


vocabulary_size=2000  #Ԥ����Ƶ�����ʿ�ĳ���
count=[['UNK',-1]]    #��ʼ������Ƶ��ͳ�Ƽ���

'''
1.��@param ��words���г��ֹ��ĵ�����Ƶ��ͳ�ƣ�ȡtop 1999Ƶ���ĵ��ʷ���dictionary�У��Ա���ٲ�ѯ��
2.�����������Ȿ�����ʿ⡱@param��words�����룬������top 1999֮��ĵ��ʣ�ͳһ����Ϊ��UNK����δ֪�������Ϊ0����ͳ����Щ���ʵ�������
@return: ���������Ȿ��ı���data��ÿ�����ʵ�Ƶ��ͳ��count���ʻ��dictionary���䷴ת��ʽreverse_dictionary
'''
def build_dataset(words):
    counter=collections.Counter(words).most_common(vocabulary_size-1) #length of all counter:22159 ȡtop1999Ƶ���ĵ�����Ϊvocabulary����������Ϊunknown
    count.extend(counter)
    #�dictionary
    dictionary={}
    for word,_ in count:
        dictionary[word]=len(dictionary)
    data=[]
    #ȫ������תΪ���
    #���ж���������Ƿ������dictionary������ǣ���ת�ɱ�ţ�������ǣ���תΪ���0������UNK��
    unk_count=0
    for word in words:
        if word in dictionary:
            index=dictionary[word]
        else:
            index=0
            unk_count+=1
        data.append(index)
    count[0][1]=unk_count
    reverse_dictionary=dict(zip(dictionary.values(),dictionary.keys()))
    return data,count,dictionary,reverse_dictionary

data,count,dictionary,reverse_dictionary=build_dataset(words)   
del words #ɾ��ԭʼ�����б���Լ�ڴ�



data_index=0


'''
����Skip-Gramģʽ
����word2vecѵ������
@param batch_size:ÿ������ѵ����������
@param num_skips: Ϊÿ���������ɶ�������������ʵ����2������batch_size������num_skips��������,��������ȷ����һ��Ŀ��ʻ����ɵ�������ͬһ�������С�
@param skip_window:������Զ������ϵ�ľ��루����ʵ����Ϊ1����Ŀ�굥��ֻ�ܺ����ڵ���������������������2*skip_window>=num_skips
'''
def generate_batch(batch_size,num_skips,skip_window):
    global data_index
    assert batch_size%num_skips==0
    assert num_skips<=2*skip_window
    batch=np.ndarray(shape=(batch_size),dtype=np.int32)
    labels=np.ndarray(shape=(batch_size,1),dtype=np.int32)
    span=2*skip_window+1   #��ӳ���
    buffer=collections.deque(maxlen=span)
    
    for _ in range(span):  #˫����������ʼֵ
        buffer.append(data[data_index])
        data_index=(data_index+1)%len(data)  
        
    for i in range(batch_size//num_skips):  #��һ��ѭ����i��ʾ�ڼ�����˫�����deque
        for j in range(span):  #�ڲ�ѭ��������deque
            if j>skip_window:
                batch[i*num_skips+j-1]=buffer[skip_window]
                labels[i*num_skips+j-1,0]=buffer[j]
            elif j==skip_window:
                continue
            else:
                batch[i*num_skips+j]=buffer[skip_window]
                labels[i*num_skips+j,0]=buffer[j]
        buffer.append(data[data_index])  #���һ�����ʣ�����һ������
        data_index=(data_index+1)%len(data)
    return batch,labels    


#��ʼѵ��
batch_size=128   
embedding_size=128
skip_window=1
num_skips=2
num_sampled=64  #ѵ��ʱ���������������������ʵ�����
#��֤����
valid_size=16 #��ȡ����֤������
valid_window=100 #��֤����ֻ��Ƶ����ߵ�100�������г�ȡ
valid_examples=np.random.choice(valid_window,valid_size,replace=False)#���ظ���0����10l��ȡ16��


graph=tf.Graph()
with graph.as_default():
    train_inputs=tf.placeholder(tf.int32, shape=[batch_size])
    train_labels=tf.placeholder(tf.int32, shape=[batch_size,1])
    valid_dataset=tf.constant(valid_examples,dtype=tf.int32)
    embeddings=tf.Variable(tf.random_uniform([vocabulary_size,embedding_size], -1, 1))   #��ʼ��embedding vector
    embed=tf.nn.embedding_lookup(embeddings, train_inputs) 
    
    #��NCE loss��Ϊ�Ż�ѵ����Ŀ�� 
    nce_weights=tf.Variable(tf.truncated_normal([vocabulary_size,embedding_size], stddev=1.0/np.math.sqrt(embedding_size)))
    nce_bias=tf.Variable(tf.zeros([vocabulary_size]))
    loss=tf.reduce_mean(tf.nn.nce_loss(nce_weights, nce_bias, embed, train_labels, num_sampled, num_classes=vocabulary_size))
    optimizer=tf.train.GradientDescentOptimizer(1.0).minimize(loss)
    norm=tf.sqrt(tf.reduce_sum(tf.square(embeddings), axis=1, keep_dims=True))
    normalized_embeddings=embeddings/norm   #������L2������õ���׼�����normalized_embeddings
    
    valid_embeddings=tf.nn.embedding_lookup(normalized_embeddings,valid_dataset)    #����������64����ô��Ӧ��embedding��normalized_embeddings��64�е�vector
    similarity=tf.matmul(valid_embeddings,normalized_embeddings,transpose_b=True)   #������֤���ʵ�Ƕ��������ʻ�������е��ʵ�������
    
    init=tf.global_variables_initializer()
    
num_steps=1000001
with tf.Session(graph=graph) as session:
    init.run()
    print("Initialized")
    avg_loss=0
    for step in range(num_steps):
        batch_inputs,batch_labels=generate_batch(batch_size, num_skips, skip_window)  #��������ѵ������
        feed_dict={train_inputs:batch_inputs,train_labels:batch_labels}   #��ֵ
        _,loss_val=session.run([optimizer,loss],feed_dict=feed_dict)
        avg_loss+=loss_val
        if step % 2000 ==0:
            if step>0:
                avg_loss/=2000
            print("Avg loss at step ",step,": ",avg_loss)
            avg_loss=0
        if step%10000==0:
            sim=similarity.eval()
            for i in range(valid_size):
                valid_word=reverse_dictionary[valid_examples[i]]  #�õ���֤����
                top_k=8  
                nearest=(-sim[i,:]).argsort()[1:top_k+1]     #ÿһ��valid_example���ƶ���ߵ�top-k������
                log_str="Nearest to %s:" % valid_word
                for k in range(top_k):
                    close_word=reverse_dictionary[nearest[k]]
                    log_str="%s %s," %(log_str,close_word)
                print(log_str)
    final_embedding=normalized_embeddings.eval()
'''
���ӻ�Word2Vecɢ��ͼ������
'''
def plot_with_labels(low_dim_embs,labels,filename):
    assert low_dim_embs.shape[0]>=len(labels),"more labels than embedding"
    plt.figure(figsize=(18,18))
    for i,label in enumerate(labels):
        x,y=low_dim_embs[i,:]
        plt.scatter(x, y)
        plt.annotate(label,xy=(x,y),xytext=(5,2),textcoords='offset points',ha='right',va='bottom')
    plt.savefig(filename)

'''
tsneʵ�ֽ�ά����ԭʼ��128ά��Ƕ����������2ά
'''

tsne=TSNE(perplexity=30,n_components=2,init='pca',n_iter=5000)
plot_number=150
low_dim_embs=tsne.fit_transform(final_embedding[:plot_number,:])
labels=[reverse_dictionary[i] for i in range(plot_number)]
plot_with_labels(low_dim_embs, labels, './plot.png')

       

    