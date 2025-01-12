#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2021-07-24 11:30:23
# @Author  : Chenghao Mou (mouchenghao@gmail.com)

from typing import List
from datasketch import MinHash, MinHashLSH
from nltk.util import ngrams
from text_dedup.utils.group import get_group_indices
import multiprocessing as mp
import time

class MinHashDeduper:


    def __init__(self, num_perm: int = 128, threshold: float = 0.5, ngram_size: int = 5):

        self.num_perm = num_perm
        self.threshold = threshold
        self.ngram_size = ngram_size
        self.lsh = None

    def fit_transform(self, data: List[str]) -> List[int]:
        """Group similar documents with minhash.

        Parameters
        ----------
        data : List[str]
            List of document strings.

        Returns
        -------
        List[int]
            List of group indices.
        
        Examples
        --------
        >>> deduper = MinHashDeduper(ngram_size=5, threshold=0.3)
        >>> groups = deduper.fit_transform(["This is a sentence.", "This is another sentence.", "This is a question.", "hello world"])
        >>> groups
        [0, 0, 2, 3]
        """
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        signatures = []
        for i, doc in enumerate(data):
            m = MinHash(num_perm=self.num_perm)
            for ngram in ngrams(doc, self.ngram_size):
                m.update(''.join(ngram).encode('utf-8'))
            signatures.append(m)
            self.lsh.insert(f'm{i}', m)
        
        neighbors = []
        for i, doc in enumerate(data):
            result = self.lsh.query(signatures[i])
            neighbors.append([int(x[1:]) for x in result])
        
        return get_group_indices(neighbors)


    def fit_transform_parallel(self, data: List[str]) -> List[int]:
        """Group similar documents with minhash.

        Parameters
        ----------
        data : List[str]
            List of document strings.

        Returns
        -------
        List[int]
            List of group indices.

        Examples
        --------
        >>> deduper = MinHashDeduper(ngram_size=5, threshold=0.3)
        >>> groups = deduper.fit_transform(["This is a sentence.", "This is another sentence.", "This is a question.", "hello world"])
        >>> groups
        [0, 0, 2, 3]
        """

        pool = mp.Pool(mp.cpu_count())
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)

        signatures = [pool.apply_async(_create_signature, args=(self.num_perm, self.ngram_size, doc)) for doc in data]

        for i, m in enumerate(signatures):
            signatures[i] = m.get()

        for i, m in enumerate(signatures):
            self.lsh.insert(f'm{i}', m)

        # Does not work for some reason, although it does not affect performance that much
        # query_results = [pool.apply_async(self.lsh.query, args=(s)) for s in signatures]
        # for i, qr in enumerate(query_results):
            # query_results[i] = qr.get()

        neighbors = []
        for i, doc in enumerate(data):
            result = self.lsh.query(signatures[i])
            # result = query_results[i]
            neighbors.append([int(x[1:]) for x in result])

        pool.close()
        pool.join()

        return get_group_indices(neighbors)


def _create_signature(num_perm, ngram_size, doc):
    m = MinHash(num_perm=num_perm)
    for ngram in ngrams(doc, ngram_size):
        m.update(''.join(ngram).encode('utf-8'))
    return m
        
        
