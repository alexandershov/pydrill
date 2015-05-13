import random


def integer(min_value, max_value):
    return random.randint(min_value, max_value)


def var_name():
    return random.choice(['x', 'y', 'z'])
