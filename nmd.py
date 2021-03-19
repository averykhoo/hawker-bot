import itertools
from typing import Sequence
from typing import Union


def ngram_movers_distance(word_1: str,
                          word_2: str,
                          n: int = 2,
                          invert: bool = False,
                          normalize: bool = False,
                          ) -> float:
    """
    calculates the n-gram mover's distance between two words (for some specified n)
    case-sensitive by default, so lowercase/casefold the input words for case-insensitive results

    :param word_1: a string
    :param word_2: another string, or possibly the same string
    :param n: number of chars per n-gram (default 2)
    :param invert: return similarity instead of difference
    :param normalize: normalize to a score from 0 to 1 (inclusive of 0 and 1)
    :return: n-gram mover's distance, possibly inverted and/or normalized
    """
    # sanity checks
    if not isinstance(word_1, str):
        raise TypeError(word_1)
    if '\2' in word_1 or '\3' in word_1:
        raise ValueError(word_1)

    if not isinstance(word_2, str):
        raise TypeError(word_2)
    if '\2' in word_2 or '\3' in word_2:
        raise ValueError(word_2)

    if not isinstance(n, int):
        raise TypeError(n)
    if n < 2:
        raise ValueError(n)  # technically it would work for n==1, but we'd want to drop the START and END flags

    # add START_TEXT and END_TEXT markers to each word
    # https://en.wikipedia.org/wiki/Control_character#Transmission_control
    # the usage of these characters in any text is almost certainly a bug
    word_1 = f'\2{word_1}\3'
    word_2 = f'\2{word_2}\3'

    # number of n-grams per word
    num_grams_1 = len(word_1) - n + 1
    num_grams_2 = len(word_2) - n + 1

    # generate n_gram indices and index their locations
    n_gram_locations_1 = dict()
    for idx in range(num_grams_1):
        n_gram_locations_1.setdefault(word_1[idx:idx + n], []).append(idx / (num_grams_1 - 1))
    n_gram_locations_2 = dict()
    for idx in range(num_grams_2):
        n_gram_locations_2.setdefault(word_2[idx:idx + n], []).append(idx / (num_grams_2 - 1))

    # we want to calculate the earth mover distance for all n-grams in both words, which uses the following equation:
    # > distance = sum(emd_1d(n_gram_locations_1.get(n_gram, []), n_gram_locations_2.get(n_gram, []))
    # >                for n_gram in set(n_gram_locations_1).union(set(n_gram_locations_2)))
    # this could be optimized by only calculating emd for n-grams in common and just counting the symmetric difference
    # but calculating similarity (i.e. inverted distance) runs even faster than that
    # so instead we calculate the similarity and then find distance using the following identity:
    # > distance + similarity == num_grams_1 + num_grams_2
    similarity = 0
    for n_gram, locations_1 in n_gram_locations_1.items():
        if n_gram in n_gram_locations_2:
            similarity += len(locations_1) + len(n_gram_locations_2[n_gram])
            similarity -= _emd_1d_fast(locations_1, n_gram_locations_2[n_gram])

    # return similarity or distance, optionally normalized
    output = similarity if invert else num_grams_1 + num_grams_2 - similarity
    if normalize:
        output /= num_grams_1 + num_grams_2
    return output


def _emd_1d_fast(positions_x: Sequence[Union[int, float]],
                 positions_y: Sequence[Union[int, float]],
                 ) -> float:
    # x will be the longer list
    if len(positions_x) < len(positions_y):
        positions_x, positions_y = positions_y, positions_x

    # y is empty, so just count the x items and exit early
    if len(positions_y) == 0:
        return float(len(positions_x))

    # y has only one item, so take min distance and count the rest of the x items
    if len(positions_y) == 1:
        return float(min(abs(x - positions_y[0]) for x in positions_x) + len(positions_x) - 1)

    # make a COPY of the list, sorted in reverse (descending order)
    # we'll be modifying x and y in-place later, and we don't want to accidentally edit the input
    # also the input might be a tuple, you never know
    positions_x = sorted(positions_x, reverse=True)
    positions_y = sorted(positions_y, reverse=True)

    # if there are exactly the same number of objects in both lists
    # then there must be a 1-to-1 correspondence, so we can just zip the lists together
    # note that this step requires both lists to be sorted (both being in reverse is fine)
    if len(positions_x) == len(positions_y):
        return float(sum(abs(x - y) for x, y in zip(positions_x, positions_y)))

    # remove any matching points in x and y
    # this implementation also reverses the list (i.e. descending -> ascending)
    # matching points contribute 0 distance, so we don't need to account for them
    new_x = []
    new_y = []
    while positions_x and positions_y:
        if positions_x[-1] < positions_y[-1]:
            new_x.append(positions_x.pop(-1))
        elif positions_y[-1] < positions_x[-1]:
            new_y.append(positions_y.pop(-1))
        else:  # discard matching points in x and y
            positions_x.pop(-1)
            positions_y.pop(-1)
    if positions_x:
        positions_x.reverse()
        new_x.extend(positions_x)
    if positions_y:
        positions_y.reverse()
        new_y.extend(positions_y)
    positions_x = new_x
    positions_y = new_y

    # there are no more duplicates across both lists
    # there can still be duplicates within each list, but that's okay
    # both lists are now sorted normally (in ascending order)
    # we also know that the lists do not have the same number of items
    # after having removed duplicate items, this is the last chance to early exit
    if len(positions_y) == 0:
        return float(len(positions_x))
    if len(positions_y) == 1:
        return float(min(abs(x - positions_y[0]) for x in positions_x) + len(positions_x) - 1)

    # now is the hard part of the algorithm, matching possible points from both lists
    # [x1 y1 x2 x3 x4 y2 x3] ==> [x1 y1 x2], [x4 y2 x5] (x3 can never be matched)
    # we'll break the x-y matching problem into sub-problems which can be solved separately
    # the obvious thing to do is to build a bipartite graph and look for connected components
    # but implementing the full graph building and separation algorithm would eat too many cpu cycles
    # so instead we'll use a counting method to find the ranges of x and y that map the each other
    # we'll start by merging the lists in order to find which x can be mapped to from each y
    # thanks to timsort, this merge happens in more or less linear time
    locations = sorted([(loc, False) for loc in positions_x] + [(loc, True) for loc in positions_y])
    component_ranges = []

    # get ranges of FORWARD possible alignments
    n = 0
    current_left = None
    for idx, (loc, is_y) in enumerate(locations):
        if is_y:
            n += 1
            if current_left is None:
                current_left = idx
        elif n > 0:
            n -= 1
            if n == 0:
                component_ranges.append((current_left, idx))
                current_left = None
    if current_left is not None:  # current_left could be 0, so don't just test truthiness
        component_ranges.append((current_left, len(locations) - 1))

    # get ranges of BACKWARD possible alignments
    n = 0
    current_right = None
    for idx in range(len(locations) - 1, -1, -1):
        if locations[idx][1]:  # if is_y:
            n += 1
            if current_right is None:
                current_right = idx
        elif n > 0:
            n -= 1
            if n == 0:
                component_ranges.append((idx, current_right))
                current_right = None
    if current_right is not None:
        component_ranges.append((0, current_right))

    # we'll accumulate distance as we simplify the problem
    distance = 0.0

    # merge ranges to get the sets of connected components
    component_ranges.sort(reverse=True)
    last_seen = -1
    while component_ranges:
        # take the first range, then keep taking overlapping ranges
        left, right = component_ranges.pop(-1)
        while component_ranges and component_ranges[-1][0] <= right:
            right = max(right, component_ranges.pop(-1)[1])  # range can be a proper subset

        # count unmatched points since last seen
        if left > last_seen + 1:
            distance += left - last_seen - 1  # count unmatchable points

        # split the range into x and y lists again, in reverse (descending order)
        connected_x = [idx for idx, is_y in locations[right:left - 1 if left else None:-1] if not is_y]
        connected_y = [idx for idx, is_y in locations[right:left - 1 if left else None:-1] if is_y]

        # greedy-match constrained points with only one possible match at the SMALLER end of connected_y
        while connected_y:  # don't need to check connected_x since it cannot be shorter than y
            # if y_min <= x_min, then they must be paired
            if connected_y[-1] <= connected_x[-1]:
                distance += connected_x.pop(-1) - connected_y.pop(-1)

            # x_min < y_min < x_next and abs(y_min - x_min) <= abs(y_min - x_next)
            # meaning that y_min's best option is x_min, for which there are no competing points
            elif len(connected_x) >= 2 \
                    and connected_y[-1] < connected_x[-2] \
                    and (connected_y[-1] - connected_x[-1]) <= (connected_x[-2] - connected_y[-1]):
                distance += connected_y.pop(-1) - connected_x.pop(-1)

            # endpoints do not match, break loop
            else:
                break

        # reverse both lists IN PLACE, so now they are sorted in ascending order
        connected_x.reverse()
        connected_y.reverse()

        # greedy-match constrained points with only one possible match at the LARGER end of connected_y
        while connected_y:
            # if y_max >= x_max, then they must be paired
            if connected_y[-1] >= connected_x[-1]:
                distance += connected_y.pop(-1) - connected_x.pop(-1)

            # x_prev < y_max < x_max and abs(y_max - x_max) <= abs(y_max - x_prev)
            # meaning that y_max's best option is x_max, for which there are no competing points
            elif len(connected_x) >= 2 \
                    and connected_y[-1] > connected_x[-2] \
                    and (connected_x[-1] - connected_y[-1]) <= (connected_y[-1] - connected_x[-1]):
                distance += connected_y.pop(-1) - connected_x.pop(-1)

            # endpoints don't match
            else:
                break

        # try for early exit, because itertools.combinations is slow
        if len(connected_y) == 0:
            distance += len(connected_x)
        elif len(connected_y) == 1:
            distance += float(min(abs(x - connected_y[0]) for x in connected_x)) + len(connected_x) - 1

        # enumerate all possible matches for this connected component
        # this code block works even if connected_y is empty
        # possible: try to greedy-match unshared points (greedy match must succeed for all y)
        # also possible: actually build the bipartite graph to exclude impossible match options
        else:
            costs = [len(connected_y)]
            for x_combination in itertools.combinations(connected_x, len(connected_y)):
                costs.append(sum(abs(x - y) for x, y in zip(x_combination, connected_y)))
            distance += min(costs) + len(connected_x) - len(connected_y)

        # update last seen
        last_seen = right

    # count unmatched points after last seen
    if len(locations) > last_seen + 1:
        distance += len(locations) - last_seen - 1

    return distance


def _emd_1d_slow(positions_x: Sequence[float],
                 positions_y: Sequence[float],
                 ) -> float:
    # positions_x must be longer
    if len(positions_x) < len(positions_y):
        positions_x, positions_y = positions_y, positions_x

    # sort both lists
    positions_x = sorted(positions_x)
    positions_y = sorted(positions_y)

    # find the minimum cost alignment
    costs = [len(positions_y)]
    for x_combination in itertools.combinations(positions_x, len(positions_y)):
        costs.append(sum(abs(x - y) for x, y in zip(x_combination, positions_y)))

    # the distance is the min cost alignment plus a count of unmatched points
    return len(positions_x) - len(positions_y) + min(costs)


def emd_1d(positions_x: Sequence[float],
           positions_y: Sequence[float],
           ) -> float:
    """
    kind of like earth mover's distance
    but positions are limited to within the unit interval
    and must be quantized

    :param positions_x: list of positions (each a float from 0 to 1 inclusive)
    :param positions_y: list of positions (each a float from 0 to 1 inclusive)
    :return:
    """

    # sanity checks
    assert isinstance(positions_x, Sequence)
    assert isinstance(positions_y, Sequence)
    assert all(isinstance(x, (int, float)) for x in positions_x)
    assert all(isinstance(y, (int, float)) for y in positions_y)

    # all inputs must be in the unit interval
    assert all(0 <= x <= 1 for x in positions_x)
    assert all(0 <= y <= 1 for y in positions_y)

    # run both slow and fast and check them
    answer_fast = _emd_1d_fast(positions_x, positions_y)
    answer_slow = _emd_1d_slow(positions_x, positions_y)
    assert abs(answer_fast - answer_slow) < 0.00000001, (answer_slow, answer_fast, positions_x, positions_y)
    return answer_fast


if __name__ == '__main__':

    from levenshtein import damerau_levenshtein_distance
    from levenshtein import edit_distance


    def speed_test(word_1: str, word_2: str):
        edit_distance(word_1, word_2)
        damerau_levenshtein_distance(word_1, word_2)
        return ngram_movers_distance(word_1, word_2)


    num_x = 3
    num_y = 7

    xs = [i / (num_x - 1) for i in range(num_x)]
    ys = [i / (num_y - 1) for i in range(num_y)]
    # print(xs)
    # print(ys)
    xs = xs + xs + xs

    for x_len in range(len(xs) + 1):
        for y_len in range(len(ys) + 1):
            print(x_len, y_len)
            for x_combi in itertools.combinations(xs, x_len):
                for y_combi in itertools.combinations(ys, y_len):
                    assert abs(emd_1d(x_combi, y_combi) - emd_1d(y_combi, x_combi)) < 0.0001, (x_combi, y_combi)

    for _ in range(1000):
        speed_test('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                   'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        speed_test('aabbbbbbbbaa', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        speed_test('aaaabbbbbbbbaaaa', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        speed_test('banana', 'bababanananananananana')
        speed_test('banana', 'bababanananananananananna')
        speed_test('banana', 'nanananananabababa')
        speed_test('banana', 'banana')
        speed_test('nanananananabababa', 'banana')
        speed_test('banana', 'bababananananananananannanananananananana')
        speed_test('banana', 'bababananananananananannananananananananananananananannanananananananana')
        speed_test('bananabababanana', 'bababananananananananannananananananananananananananannananabanananananana')

    # test cases: https://www.watercoolertrivia.com/blog/schwarzenegger
    with open('schwarzenegger.txt') as f:
        for line in f:
            print('schwarzenegger', line.strip(), speed_test(line.strip(), 'schwarzenegger'))

    # real world test cases
    with open('words_en.txt') as f1:
        with open('words_ms.txt') as f2:
            for en, ms in zip(f1, f2):
                speed_test(en.strip(), ms.strip())
                speed_test(en.strip(), en.strip())
                speed_test(ms.strip(), ms.strip())
