from django import forms

class ClusterizationParams(forms.Form):
    tokenizer = forms.CharField(label='Tokenizer', max_length=100)
    w2v_size = forms.IntegerField(label='Word2Vec Embedding Vector Size')
    w2v_window = forms.IntegerField(label='Word2Vec Window Size')
    min_samples = forms.IntegerField(label='min_samples for DBSCAN Algorithm')