from django.shortcuts import render

import json
import os
import sys
import numpy as np
from kneed import KneeLocator
import nltk
from nltk.tokenize import TreebankWordTokenizer
nltk.download('words')
nltk.download('stopwords')
from gensim.models import Word2Vec
import math
import pyonmttok
from sklearn.neighbors import NearestNeighbors
import daal4py
import re
import time
import logging
from statistics import mean, stdev
import matplotlib.pyplot as plt
import multiprocessing
from statistics import mean, stdev
from fuzzywuzzy import fuzz
import pandas as pd
from django.http import JsonResponse
from django.views import View
from ESReader.models import Errors

class LogClustering(View):

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        filename="logs_cluster.log",
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    def get(self, request):
        self.tokenizer = request.GET.get('tokenizer', 'nltk')
        self.w2v_size = int(request.GET.get('w2v_size', 100))
        self.w2v_window = int(request.GET.get('w2v_window', 5))
        self.min_samples = int(request.GET.get('min_samples', 1))

        data = {}
        t0 = time.time()

        self.cpu_number = multiprocessing.cpu_count()
        errors = Errors.objects.values_list('error_message', flat=True)
        self.errors = list(errors)
        self.tokenized = self.data_preparation()
        self.word2vec = self.tokens_vectorization()
        self.sent2vec = self.sentence_vectorization()
        self.tuning_parameters()
        self.cluster_labels = self.dbscan()

        t1 = time.time()
        logging.info("Total time: {}".format(t1-t0))

        self.save()

        self.model = list(Errors.objects.all().values())
        data["clustered"] = self.clustered_errors()

        return JsonResponse(data)

    def data_preparation(self):
        self.clear_strings()
        return self.tokenization()

    def tuning_parameters(self):
        self.distances = self.kneighbors()
        #self.distance_curve(self.distances)
        self.epsilon = self.epsilon_search()

    @staticmethod
    def remove_whitespaces(sentence):
        """
        Some error messages has multiple spaces, so we change it to one space.
        :param sentence:
        :return:
        """
        return " ".join(sentence.split())

    def clear_strings(self):
        """
        Clear error messages from unnecessary data:
        - UID/UUID in file paths
        - line numbers - as an example "error at line number ..."
        Removed parts of text are substituted with titles
        :param data:
        :return:
        """
        logging.info("strings preparation is started")
        _uid = r'[0-9a-zA-Z]{12,128}'
        _line_number = r'(at line[:]*\s*\d+)'
        _uuid = r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}'

        for idx, item in enumerate(self.errors):
            _cleaned = re.sub(_line_number, "at line LINE_NUMBER", item)
            _cleaned = re.sub(_uid, "UID", _cleaned)
            _cleaned = re.sub(_uuid, "UUID", _cleaned)
            self.errors[idx] = self.remove_whitespaces(_cleaned)
        logging.info("finished")

    def tokenization(self, mode='nltk'):
        """
        Tokenization of a list of error messages.
        The best tokenizer for error messages is TreebankWordTokenizer (nltk).
        It's good at tokenizing file paths.
        Alternative tokenizer. It performs much faster, but worse in tokenizing of paths.
        It splits all paths by "/".
        TODO: This method should be optimized to the same tokenization quality as TreebankWordTokenizer
        :param errors:
        :return:
        """
        logging.info("Stage 1: Tokenization was started")
        tokenized = []
        if mode == 'nltk':
            for line in self.errors:
                tokenized.append(TreebankWordTokenizer().tokenize(line))
            logging.info("Stage 1 finished")
        elif mode == 'pyonmttok':
            tokenizer = pyonmttok.Tokenizer("space", joiner_annotate=False, segment_numbers=False)
            for doc in self.errors:
                tokens, features = tokenizer.tokenize(doc)
                tokenized.append(tokens)
        return tokenized

    def tokens_vectorization(self, min_count=1, iter=10):
        """
        Training word2vec model
        :param sentences: tokenized sentences (recommended value is 100)
        :param size: size of the vector to represent each token (recommended value is 5)
        :param window: max distance between target token and its neighbors (recommended value is 5)
        :param min_count: minimium frequency count of words (recommended value is 1)
        :param workers: number of CPUs
        :param iter: (recommended value is 10)
        :return:
        """
        logging.info("Stage 2: Word2Vec training started")
        word2vec = Word2Vec(self.tokenized, size=self.w2v_size, window=self.w2v_window,
                            min_count=min_count, workers=self.cpu_number, iter=iter)
        logging.info("Stage 2 finished")
        return word2vec

    def sentence_vectorization(self):
        """
        Calculates mathematical average of the word vector representations
        of all the words in each sentence
        :param sentences: tokenized
        :param model: word2vec model
        :return:
        """
        logging.info("Stage 3: Sentence2Vec started")
        sent2vec = []
        for sent in self.tokenized:
            sent_vec = []
            numw = 0
            for w in sent:
                try:
                    if numw == 0:
                        sent_vec = self.word2vec[w]
                    else:
                        sent_vec = np.add(sent_vec, self.word2vec[w])
                    numw += 1
                except:
                    pass

            sent2vec.append(np.asarray(sent_vec) / numw)
        logging.info("Stage 3 finished")
        return np.array(sent2vec)

    def kneighbors(self):
        """
        Calculates average distances for k-nearest neighbors
        :param X:
        :return:
        """
        logging.info("Stage 4.1: K-neighbors distances started")
        k = round(math.sqrt(len(self.sent2vec)))
        neigh = NearestNeighbors(n_neighbors=k)
        nbrs = neigh.fit(self.sent2vec)
        distances, indices = nbrs.kneighbors(self.sent2vec)
        distances = np.sort(distances, axis=0)
        if k > 2:
            avg_distances = []
            for line in distances:
                avg_distances.append(mean(line))
            return avg_distances
        else:
            return distances[:, 1]

    def epsilon_search(self):
        """
        Search epsilon for DBSCAN
        :param distances:
        :return:
        """
        logging.info("Stage 4.2: Epsilon search started")
        kneedle = KneeLocator(self.distances, list(range(len(self.distances))))
        logging.info("Stage 4.2 finished")
        if len(kneedle.all_elbows)>0:
            return max(kneedle.all_elbows)
        else:
            return 1

    @staticmethod
    def distance_curve(distances):
        """
        Save distance curve with knee candidates in file.
        :param distances:
        :return:
        """
        sensitivity = [1, 3, 5, 10, 100, 150, 200]
        knees = []
        y = list(range(len(distances)))
        for s in sensitivity:
            kl = KneeLocator(distances, y, S=s)
            knees.append(kl.knee)

        plt.style.use('ggplot');
        plt.figure(figsize=(10, 10))
        plt.plot(distances, y)
        colors = ['r', 'g', 'k', 'm', 'c', 'b', 'y']
        for k, c, s in zip(knees, colors, sensitivity):
            plt.vlines(k, 0, len(distances), linestyles='--', colors=c, label=f'S = {s}')
            plt.legend()
            plt.savefig("distance_curve.png")

    def dbscan(self):
        """
        DBSCAN clusteing with daal4py library
        :param X:
        :param epsilon:
        :return: DBSCAN labels
        """
        logging.info("Stage 4.3: DBSCAN started")
        algo = daal4py.dbscan(minObservations=self.min_samples, epsilon=self.epsilon,
                              resultsToCompute='computeCoreIndices|computeCoreObservations')
        result = algo.compute(self.sent2vec)
        logging.info("Stage 4.3 finished")
        return result.assignments[:, 0].tolist()

    def save(self):
        errors = Errors.objects.all()
        logging.info(errors)
        for idx, obj in enumerate(errors):
            obj.cluster_label = self.cluster_labels[idx]
            obj.save()

    def clustered_errors(self):
        results = {}
        for label in set(self.cluster_labels):
            elements = []
            for idx, l in enumerate(self.cluster_labels):
                if l == label:
                    elements.append(self.errors[idx])
            results[label] = elements
        return results

    def errors_in_cluster(self, cluster_label):
        results = []
        for idx, l in enumerate(self.cluster_labels):
            if l == cluster_label:
                results.append(self.errors[idx])
        return results

    def cluster_statistics(self):
        clusters = []
        for item in self.clustered_errors:
            cluster = {}
            cluster["cluster_name"] = item
            cluster["first_entry"] = self.clustered_errors[item][0]
            cluster["cluster_size"] = len(self.clustered_errors[item])
            lengths = []
            for s in self.clustered_errors[item]:
                lengths.append(len(s))
            mean_length = mean(lengths)
            try:
                std_length = stdev(lengths)
            except:
                std_length = 0
            cluster["mean_length"] = mean_length
            cluster["std_lengt"] = std_length
            x0 = self.clustered_errors[item][0]
            dist = []
            for i in range(0, len(self.clustered_errors[item])):
                x = self.clustered_errors[item][i]
                dist.append(fuzz.ratio(x0, x))
            cluster["mean_similarity"] = mean(dist)
            try:
                cluster["std_similarity"] = stdev(dist)
            except:
                cluster["std_similarity"] = 0
            clusters.append(cluster)
        clusters_df = pd.DataFrame(clusters)
        return clusters_df.sort_values(by=['mean_similarity'])
