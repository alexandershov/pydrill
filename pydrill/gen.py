from functools import partial
import random


def integer(min_value, max_value):
    return random.randint(min_value, max_value)


def var_name(n=1):
    var_names = ['x', 'y', 'z']
    if n == 1:
        return random.choice(var_names)
    return random.sample(var_names, n)


def choice(seq):
    return random.choice(seq)


def nested_list(num_lists=2, num_items=2, make_value=partial(integer, 1, 5), with_flat=True):
    nested = [[make_value() for j in range(num_items)]
              for i in range(num_lists)]
    if with_flat:
        return nested, sum(nested, [])
    return nested
