from nltk.tree import Tree


def draw_with_nltk(root_node, hide_terminals=True):
    hidden_terminals = {"(", ")", "{", "}", ";"}

    def to_nltk_tree(node):
        if node.is_terminal:
            return str(node.name)

        children = []
        for child in node.children:
            converted = to_nltk_tree(child)
            if hide_terminals and isinstance(converted, str) and converted in hidden_terminals:
                continue
            children.append(converted)

        return Tree(str(node.name), children)

    nltk_tree = to_nltk_tree(root_node)
    nltk_tree.draw()
