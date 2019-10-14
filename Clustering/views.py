from django.shortcuts import render
import sys
import os
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
import matplotlib.pyplot as plt
import multiprocessing
from statistics import mean, stdev
from fuzzywuzzy import fuzz
import pandas as pd
from django.http import JsonResponse
from django.views import View
from ESReader.models import Errors
from .forms import ClusterizationParams


def safe_run(func):

    def func_wrapper(*args, **kwargs):

        try:
           return func(*args, **kwargs)

        except Exception as e:

            print(e)
            return None

    return func_wrapper


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            logging.info('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed

class LogClustering(View):

    template_name = 'clustering.html'
    form_class = ClusterizationParams
    success_url = 'cluster'

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        filename="logs_cluster.log",
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    def get(self, request, *args, **kwargs):
        data = {}
        if request.session._SessionBase__session_key is not None:
            try:
                session_id = request.session._SessionBase__session_key
                output_data = ['pandaid', 'error_message', 'modificationtime', 'error_code']
                self.cluster_labels = request.session["cluster_labels"]
                data["clustered"] = self.clustered(output_data, session_id)
                data["statistics"] = request.session["statistics"]
                data["settings"] = request.session["settings"]
                data["submitted"] = True
                return render(request, self.template_name, data)
            except:
                return render(request, self.template_name, {'form': self.form_class()})
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if request.POST.get("submitted"):
            return render(request, self.template_name, {'form': form})
        if form.is_valid():
            self.tokenizer = form.cleaned_data['tokenizer']
            self.w2v_size = form.cleaned_data['w2v_size']
            self.w2v_window = form.cleaned_data['w2v_window']
            self.min_samples = form.cleaned_data['min_samples']

            data = {}
            data['settings'] = form.cleaned_data
            t0 = time.time()

            self.cpu_number = multiprocessing.cpu_count()
            if request.session._SessionBase__session_key is not None:
                session_id = request.session._SessionBase__session_key
                errors = Errors.objects.filter(session_id=session_id).values_list('error_message', flat=True)
                self.errors = list(errors)
                self.tokenized = self.data_preparation()
                self.word2vec = self.tokens_vectorization()
                self.sent2vec = self.sentence_vectorization()
                self.tuning_parameters()
                self.cluster_labels = self.dbscan()

                t1 = time.time()
                logging.info("Total time: {}".format(t1 - t0))

                output_data = ['pandaid', 'error_message', 'modificationtime', 'error_code']
                self.clustered_errors = self.clustered(output_data, session_id)
                data["clustered"] = self.clustered_errors

                data["statistics"] = self.cluster_statistics()
                request.session['cluster_labels'] = self.cluster_labels
                request.session['statistics'] = data['statistics']
                request.session['settings'] = data['settings']

                data['submitted'] = True
                data['form'] = form
                return render(request, self.template_name, data)
            else:
                return render(request, self.template_name, {'form': form})

        return render(request, self.template_name, {'form': form})


    @safe_run
    def data_preparation(self):
        self.clear_strings()
        return self.tokenization()

    @safe_run
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

    @safe_run
    @timeit
    def clear_strings(self):
        """
        Clear error messages from unnecessary data:
        - UID/UUID in file paths
        - line numbers - as an example "error at line number ..."
        Removed parts of text are substituted with titles
        :param data:
        :return:
        """
        _uid = r'[0-9a-zA-Z]{12,128}'
        _line_number = r'(at line[:]*\s*\d+)'
        _uuid = r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}'

        for idx, item in enumerate(self.errors):
            _cleaned = re.sub(_line_number, "at line LINE_NUMBER", item)
            _cleaned = re.sub(_uid, "UID", _cleaned)
            _cleaned = re.sub(_uuid, "UUID", _cleaned)
            self.errors[idx] = self.remove_whitespaces(_cleaned)

    @safe_run
    @timeit
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

    @safe_run
    @timeit
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
        word2vec = Word2Vec(self.tokenized, size=self.w2v_size, window=self.w2v_window,
                            min_count=min_count, workers=self.cpu_number, iter=iter)
        return word2vec

    @safe_run
    @timeit
    def sentence_vectorization(self):
        """
        Calculates mathematical average of the word vector representations
        of all the words in each sentence
        :param sentences: tokenized
        :param model: word2vec model
        :return:
        """
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
        return np.array(sent2vec)

    @safe_run
    @timeit
    def kneighbors(self):
        """
        Calculates average distances for k-nearest neighbors
        :param X:
        :return:
        """
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

    @safe_run
    @timeit
    def epsilon_search(self):
        """
        Search epsilon for DBSCAN
        :param distances:
        :return:
        """
        kneedle = KneeLocator(self.distances, list(range(len(self.distances))))
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

    @safe_run
    @timeit
    def dbscan(self):
        """
        DBSCAN clusteing with daal4py library
        :param X:
        :param epsilon:
        :return: DBSCAN labels
        """
        algo = daal4py.dbscan(minObservations=self.min_samples, epsilon=self.epsilon,
                              resultsToCompute='computeCoreIndices|computeCoreObservations')
        result = algo.compute(self.sent2vec)
        return result.assignments[:, 0].tolist()

    #
    # def save(self, session_id):
    #     errors = Errors.objects.filter(session_id=session_id)
    #     logging.info(errors)
    #     for idx, obj in enumerate(errors):
    #         obj.cluster_label = self.cluster_labels[idx]
    #         obj.save()

    @safe_run
    def clustered(self, output_data, session_id):
        """
        Returns dictionary of clusters with the arrays of elements
        :return:
        """
        values_list = []
        for item in output_data:
            values_list.append(Errors.objects.filter(session_id=session_id).values_list(item, flat=True))
        clusters = {}
        for label in set(self.cluster_labels):
            rows = []
            for idx, l in enumerate(self.cluster_labels):
                if l == label:
                    elements = {}
                    for i, item in enumerate(output_data):
                        elements[item] = values_list[i][idx]
                    rows.append(elements)
            clusters[str(label)] = rows
        return clusters

    @safe_run
    def clustered_errors(self, session_id):
        """
        Returns dictionary of clusters with the arrays of error messages:
        {
            "1": [100, 101, 102, ...],
            "2": [400, 405, 106, ...],
            ...
        }
        :return:
        """
        error_messages = Errors.objects.filter(session_id=session_id).values_list('error_message', flat=True)
        results = {}
        for label in set(self.cluster_labels):
            elements = []
            for idx, l in enumerate(self.cluster_labels):
                if l == label:
                    elements.append(error_messages[idx])
            results[label] = elements
        return results

    @safe_run
    def errors_in_cluster(self, cluster_label):
        results = []
        for idx, l in enumerate(self.cluster_labels):
            if l == cluster_label:
                results.append(self.errors[idx])
        return results

    @safe_run
    def cluster_statistics(self):
        clusters = []
        for item in self.clustered_errors:
            cluster = {}
            cluster["cluster_name"] = item
            cluster["first_entry"] = self.clustered_errors[item][0]['error_message']
            cluster["cluster_size"] = len(self.clustered_errors[item])
            lengths = []
            for s in self.clustered_errors[item]:
                lengths.append(len(s['error_message']))
            mean_length = mean(lengths)
            try:
                std_length = stdev(lengths)
            except:
                std_length = 0
            cluster["mean_length"] = mean_length
            cluster["std_lengt"] = std_length
            x0 = self.clustered_errors[item][0]['error_message']
            dist = []
            for i in range(0, len(self.clustered_errors[item])):
                x = self.clustered_errors[item][i]['error_message']
                dist.append(fuzz.ratio(x0, x))
            cluster["mean_similarity"] = mean(dist)
            try:
                cluster["std_similarity"] = stdev(dist)
            except:
                cluster["std_similarity"] = 0
            clusters.append(cluster)
        clusters_df = pd.DataFrame(clusters).round(2)
        return clusters_df.T.to_dict()

class LogClusteringService(LogClustering):

    def get(self, request):

        self.cpu_number = multiprocessing.cpu_count()
        self.tokenizer = request.GET.get('tokenizer', 'nltk')
        self.w2v_size = int(request.GET.get('w2v_size', 100))
        self.w2v_window = int(request.GET.get('w2v_window', 5))
        self.min_samples = int(request.GET.get('min_samples', 1))

        data = {}

        data['settings'] = {'cpu_number': self.cpu_number,
                            'tokenizer': self.tokenizer,
                            'w2v_size': self.w2v_size,
                            'w2v_window': self.w2v_window,
                            'min_samples': self.min_samples}

        if request.session._SessionBase__session_key is not None:
            session_id = request.session._SessionBase__session_key

        errors = Errors.objects.filter(session_id==session_id).values_list('error_message', flat=True)
        self.errors = list(errors)
        t0 = time.time()
        self.tokenized = self.data_preparation()
        self.word2vec = self.tokens_vectorization()
        self.sent2vec = self.sentence_vectorization()
        self.tuning_parameters()
        self.cluster_labels = self.dbscan()

        t1 = time.time()

        logging.info("Total time: {}".format(t1-t0))

        output_data = ['pandaid']
        updated_dict = {}
        results = self.clustered(output_data, session_id)
        for key in results:
            updated_dict[key] = [i['pandaid'] for i in results[key]]
        data["clustered"] = updated_dict

        return JsonResponse(data)