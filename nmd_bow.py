from typing import Iterable
from typing import Union

import scipy.optimize

from nmd import ngram_movers_distance
from tokenizer import unicode_tokenize


def bow_ngram_movers_distance(bag_of_words_1: Union[str, Iterable[str]],
                              bag_of_words_2: Union[str, Iterable[str]],
                              n: int = 2,
                              invert: bool = False,
                              ) -> float:
    """
    calculates the n-gram mover's distance between two bags of words (for some specified n)
    case-sensitive by default, so lowercase/casefold the input words for case-insensitive results

    :param bag_of_words_1: a list of strings
    :param bag_of_words_2: another list of strings
    :param n: number of chars per n-gram (default 2)
    :param invert: return similarity instead of distance
    :return: n-gram mover's distance, possibly inverted and/or normalized
    """

    # convert to list
    bag_of_words_1 = list(bag_of_words_1)  # rows
    bag_of_words_2 = list(bag_of_words_2)  # columns

    # optimize cost matrix using EMD
    costs = []
    for word_1 in bag_of_words_1:
        row = []
        for word_2 in bag_of_words_2:
            try:
                row.append(ngram_movers_distance(word_1, word_2, n=n, normalize=True))
            except ZeroDivisionError:
                row.append(int(word_1 != word_2))
        costs.append(row)
    if costs:
        row_idxs, col_idxs = scipy.optimize.linear_sum_assignment(costs)  # 1D equivalent of EMD
    else:
        row_idxs, col_idxs = [], []

    # sum
    if invert:
        out = min(len(bag_of_words_1), len(bag_of_words_2))
        for row_idx, col_idx in zip(row_idxs, col_idxs):
            out -= costs[row_idx][col_idx]
    else:
        out = abs(len(bag_of_words_1) - len(bag_of_words_2))
        for row_idx, col_idx in zip(row_idxs, col_idxs):
            out += costs[row_idx][col_idx]

    return out


if __name__ == '__main__':
    with open('translate-reference.txt') as f:
        ref_lines = f.readlines()
    with open('translate-google-offline.txt') as f:
        hyp_lines = f.readlines()

    scores_bow = []
    scores_nmd = []
    scores_sim = []
    for ref_line, hyp_line in zip(ref_lines, hyp_lines):
        ref_tokens = list(unicode_tokenize(ref_line.casefold(), words_only=True, merge_apostrophe_word=True))
        hyp_tokens = list(unicode_tokenize(hyp_line.casefold(), words_only=True, merge_apostrophe_word=True))
        scores_bow.append(bow_ngram_movers_distance(ref_tokens, hyp_tokens, 4) / max(len(ref_tokens), len(hyp_tokens)))
        scores_sim.append(
            bow_ngram_movers_distance(ref_tokens, hyp_tokens, 4, invert=True) / max(len(ref_tokens), len(hyp_tokens)))
        scores_nmd.append(ngram_movers_distance(' '.join(ref_tokens), ' '.join(hyp_tokens), 4, normalize=True))
        print(' '.join(ref_tokens))
        print(' '.join(hyp_tokens))
        print(scores_bow[-1])
        print(scores_sim[-1])
        print(scores_nmd[-1])

    from matplotlib import pyplot as plt

    plt.scatter(scores_bow, scores_nmd, marker='.')
    plt.show()
    scores_diff = [a - b for a, b in zip(scores_bow, scores_nmd)]
    tmp = sorted(zip(scores_diff, scores_bow, scores_sim, scores_nmd, ref_lines, hyp_lines))
    print(tmp[0])
    print(tmp[1])
    print(tmp[2])
    print(tmp[3])
    print(tmp[-1])
    print(tmp[-2])
    print(tmp[-3])
    print(tmp[-4])
