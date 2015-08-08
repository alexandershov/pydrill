from functools import partial
import random


# better named alias, used as gen.* in templates
integer = random.randint
choice = random.choice


def var_name(n=1):
    var_names = ['x', 'y', 'z']
    if n == 1:
        return random.choice(var_names)
    return random.sample(var_names, n)


def nested_list(length=2, sublist_length=2, make_value=partial(integer, 1, 5), with_flat=True):
    nested = [random_list(sublist_length, make_value) for _ in range(length)]
    if with_flat:
        return nested, sum(nested, [])
    return nested


def random_list(length, make_value):
    return [make_value() for _ in range(length)]
