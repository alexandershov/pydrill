from functools import partial
import random


# better named alias, used as gen.integer
integer = random.randint


def var_name(n=1):
    var_names = ['x', 'y', 'z']
    if n == 1:
        return random.choice(var_names)
    return random.sample(var_names, n)


def choice(seq):
    return random.choice(seq)


def nested_list(num_lists=2, num_items=2, make_value=partial(integer, 1, 5), with_flat=True):
    nested = [random_list(num_items, make_value) for _ in range(num_lists)]
    if with_flat:
        return nested, sum(nested, [])
    return nested


def random_list(length, make_value):
    return [make_value() for _ in range(length)]
