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


class Graph(object):
    def __init__(self, nodes):
        self.nodes = nodes


class Node(object):
    def __init__(self, value, connected=None):
        if connected is None:
            connected = []
        self.value = value
        self.connected = connected

    def __repr__(self):
        return 'Node(value={!r}, connected={!r})'.format(self.value, self.connected)


def get_animals():
    scooby = Node('Scooby')
    human = Node('Human')
    monkey = Node('Monkey', connected=[human])
    smart = Node('Smart', connected=[monkey, human])
    cat = Node('Cat')
    dog = Node('Dog', connected=[scooby])
    animal = Node('Animal', connected=[dog, cat, monkey, scooby])
    return Graph([animal, dog, cat, smart, monkey, human])


def class_hierarchy(graph):
    not_connected = {node.value: node for node in graph.nodes}
    for node in graph.nodes:
        for cn in node.connected:
            not_connected.pop(cn.value, None)
    roots = not_connected.values()
    root = random.choice(roots)
    path = [root]
    while root.connected:
        root = random.choice(root.connected)
        path.append(root)
    return path
