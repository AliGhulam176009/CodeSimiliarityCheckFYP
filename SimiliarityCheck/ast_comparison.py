# -*- coding : utf -8 -*-
"""
   Module for AST program comparison .

   This module implements functions for comparing .py files .
   It uses abstract syntax trees from the built in module 'ast '.

"""
import os
import sys
import logging

import ast
from _ast import *
from typing import Match, Sequence, cast

from munkres import Munkres, print_matrix

from logging import (WARN, Logger, debug, info, warning, error, critical,
                     DEBUG, INFO, WARNING, ERROR, CRITICAL,
                     basicConfig, getLogger, StreamHandler)


def compare_ASTs(ast_a: AST, ast_b: AST, reorder_depth: int) -> int:
    """
       Compare two ASTs corresponding to python programs .

       Args :
          ast_a : The first program AST to compare .
          ast_b : The first program AST to compare .
          reorder_depth : The maximum children reorder depth for better
          performance .

       Returns :
          True if the ASTs are equivalent , otherwise False .
    """

    children_a = list(ast . iter_child_nodes(ast_a))
    children_b = list(ast . iter_child_nodes(ast_b))

    info("compare_ASTs : comparing {} and {}".format(
        ast_a, ast_b))

    if ((type(ast_a) == type(ast_b))
       and len(children_a) == 0
            and len(children_b) == 0):
        debug("compare_ASTs : ASTs are equivalent and have no children")
        return 1

    if ((type(ast_a) != type(ast_b))
            or (len(children_a) != len(children_b))):
        debug("compare_ASTs : ASTs are not equivalent or not have same number of children")
        return 0

    if reorder_depth == 0:
        debug("compare_ASTs : Reordering depth is 0")
        match_index = sum(map(lambda pairs: compare_ASTs(
            pairs[0], pairs[1], reorder_depth),
            zip(children_a, children_b)))

        return match_index + 1

    elif reorder_depth > 0:
        debug("compare_ASTs : Reordering depth is > 0")
        match_index = reorder_children_compare(
            ast_a, ast_b, reorder_depth - 1)

        return match_index + 1

    return 0


def reorder_children_compare(ast_a: AST, ast_b: AST, reorder_depth: int) -> int:
    """
       Reorders child nodes and compares them .

       Args :
          ast_a : The first AST for child comparison .
          ast_b : The second AST for child comparison .
          reorder_depth : The maximum children reorder depth for better
          performance .

       Returns :
          True if there is a way to match 1-1 every child node of ast_a
          with every child node of ast_b , otherwise False .
    """
    comparison_matrix = []
    cost_matrix = []
    best_match_value = 0
    children_a = list(ast . iter_child_nodes(ast_a))
    children_b = list(ast . iter_child_nodes(ast_b))

    if len(children_a) <= 1 or len(children_b) <= 1:
        debug("reorder_children_compare : children of ASTs are <= 1")
        for child_a in children_a:
            for child_b in children_b:
                best_match_value += compare_ASTs(child_a,
                                                 child_b, reorder_depth)

    else:
        debug("reorder_children_compare : children of ASTs are > 1")
        for child_a in children_a:
            row = []
            cost_row = []
            for child_b in children_b:
                similarity = compare_ASTs(child_a, child_b, reorder_depth)
                row.append(similarity)
                cost_row.append(10000000 - similarity)

            comparison_matrix.append(row)
            cost_matrix.append(cost_row)

        # print_matrix(comparison_matrix, cost_matrix)
        indices = compute_index_matrix(cost_matrix)

        for row, col in indices:
            best_match_value += comparison_matrix[row][col]

    info("reorder_children_compare : best match value is {}".format(best_match_value))
    return best_match_value


def compute_index_matrix(cost_matrix: list) -> list:
    """
       Compute the indexes of a cost matrix .

       Args :
          cost_matrix : The cost matrix to compute the indexes of .

       Returns :
          A list of indexes of the cost matrix .
    """
    # # One way to compute the indexes of the cost matrix
    # debug("compute_index_matrix : computing indexes of cost matrix manually")

    # max_cost = max(max(cost_matrix))

    # info("compute_index_matrix : max cost is {}".format(max_cost))

    # indices = []
    # for row in range(len(cost_matrix)):
    #     for col in range(len(cost_matrix[row])):
    #         if cost_matrix[row][col] < max_cost:
    #             indices.append((row, col))

    # Another way to compute the indexes of the cost matrix
    debug("compute_index_matrix : computing indexes of cost matrix using Munkres")
    m = Munkres()
    indices = m. compute(cost_matrix)

    return indices


def compare_subtrees(sig_subtrees_p1: list, sig_subtrees_p2: list, reorder_depth: int) -> tuple:
    """
       Compare two significant subtree lists reordering up to a certain depth .

       Args :
          sig_subtrees_p1 : The first significant AST list for comparison .
          sig_subtrees_p2 : The second significant AST list for comparison .
          reorder_depth : The maximum children reorder depth for better
          performance .

       Returns :
          A tuple with the ratio of matching to non - matching nodes of the
          significant subtrees , and a list with the best matching of subtrees .
    """
    comparison_matrix = []
    cost_matrix = []
    best_match = []
    best_match_value = 0
    best_match_weight = 0

    children_a = sig_subtrees_p1 . copy()
    children_b = sig_subtrees_p2 . copy()

    if len(children_a) <= 1 or len(children_b) <= 1:
        debug("compare_subtrees : children of ASTs are <= 1")
        for child_a in children_a:
            best_match += [child_a]

            for child_b in children_b:
                best_match += [child_b]

                best_match_value += compare_ASTs(child_a,
                                                 child_b, reorder_depth)

    else:
        debug("compare_subtrees : children of ASTs are > 1")
        for child_a in children_a:
            row = []
            cost_row = []
            for child_b in children_b:
                similarity = compare_ASTs(child_a, child_b, reorder_depth)
                row . append(similarity)
                cost_row . append(10000000 - similarity)

            comparison_matrix . append(row)
            cost_matrix . append(cost_row)

        indices = compute_index_matrix(cost_matrix)

        for row, col in indices:
            best_match_weight += apply_weights_to_subtrees_mult(
                comparison_matrix[row][col], sig_subtrees_p1[row],
                sig_subtrees_p2[col])
            best_match += [sig_subtrees_p1[row], sig_subtrees_p2[col]]

    all_subtrees_weight = (
        sum(map(lambda tree: apply_weights_to_subtrees(get_num_nodes(tree),
                                                       tree), sig_subtrees_p1))
        + sum(map(lambda tree: apply_weights_to_subtrees(get_num_nodes(tree),
                                                         tree), sig_subtrees_p2)))

    print("Best match value: " + str(best_match_value))
    print("Best match weight: " + str(best_match_weight))
    print("All subtrees weight: " + str(all_subtrees_weight))

    similarity = 2 * best_match_weight / all_subtrees_weight
    info("compare_subtrees : similarity is {}".format(similarity))

    return round(similarity, 4), best_match

#AST is data type?
def get_significant_subtrees(root: AST) -> list:
    """
       Find the significant subtrees of an AST .

       Args :
          root : The root of the main AST.

       Returns :
          A list with all the significant subtrees of root .
    """
    significant_subtrees = []
    for node in ast. walk(root):
        if is_significant(node):
            significant_subtrees . append(node)

    info("get_significant_subtrees : found {} significant subtrees".format(
        [tree.__class__.__name__ for tree in significant_subtrees]))

    return significant_subtrees


def is_significant(root: AST) -> bool:
    """
       Determine if an AST is significant .

       Args :
          root : The AST whose significance we want .

       Returns :
          True for if it is significant , False otherwise .
    """
    return (isinstance(root, Import)
            or isinstance(root, FunctionDef)
            or isinstance(root, If)
            or isinstance(root, ClassDef)
            or isinstance(root, While)
            or isinstance(root, For)
            or isinstance(root, comprehension)
            or isinstance(root, Return))


def get_num_nodes(root: AST) -> int:
    """
       Find the number of nodes for a given tree .

       Args :
          root : The root of the tree whose size we want .

       Returns :
          The number of nodes in the tree .
    """
    return len(list(ast. walk(root)))


def apply_weights_to_subtrees(weight: float, subtree: AST) -> float:
    """
       Apply weights to subtrees according to the time por their roots .

       Args :
          weight : The number of nodes in the subtree .
          subtree : The subtree .

       Returns :
          The weighed weight of the tree .
    """
    new_weight = weight
    if isinstance(subtree, Module):
        new_weight *= 1
    elif isinstance(subtree, ClassDef):
        new_weight *= 1
    elif isinstance(subtree, FunctionDef):
        new_weight *= 1.2
    elif isinstance(subtree, While):
        new_weight *= 1
    elif isinstance(subtree, For):
        new_weight *= 1
    elif isinstance(subtree, comprehension):
        new_weight *= 1
    elif isinstance(subtree, Return):
        new_weight *= 1
    elif isinstance(subtree, If):
        new_weight *= 0.5
    elif isinstance(subtree, Import):
        new_weight *= 0.3

    info("apply_weights_to_subtrees : weight of {1} is {0}".format(
        new_weight, subtree.__class__.__name__))

    return new_weight


def apply_weights_to_subtrees_mult(weight: float, ast_1: AST, ast_2: AST) -> float:
    """
       Find the average weight of both trees in order to weigh the comparison .

       Args :
          weight : The weight of the comparison .
          ast_1 : The first compared tree .
          ast_2 : The second compared tree .

       Returns :
          The average of the subtrees ' weights .
    """
    if weight == 0:
        return 0
    else:
        return ((apply_weights_to_subtrees(weight, ast_1)
                 + apply_weights_to_subtrees(weight, ast_2)) / 2)

# ---------------------------------compare_many--------------------------------------------#
def compare_many(programs: list) -> list:
    """
       Compare all of the programs in the list.

       Args :
          programs : A list of strings with python programs .

       Returns :
          A matrix with the similarity rating of between all the programs .
    """

    info("compare_many : comparing {} programs".format(len(programs)))

    tree_list = list(map(
        lambda prog: get_significant_subtrees(
            ast. parse(open(prog, 'r'). read())), programs))   ##open(filename, 'r')

    info("compare_many : tree list is {}".format(tree_list))

    

    matrix = []  
    for program_1_tree_num in range(0, len(tree_list)):
        for program_2_tree_num in range(program_1_tree_num + 1, len(tree_list)):
            print("\nComparing {} to {}".format(
                program_1_tree_num, program_2_tree_num))

            subtrees1 = tree_list[program_1_tree_num]
            subtrees2 = tree_list[program_2_tree_num]

            result = compare_subtrees(subtrees1, subtrees2, 1000)

            info("Similar nodes: {}".format(
                [node.__class__.__name__ for node in result[1]]))

            matrix . append(
                (program_1_tree_num, program_2_tree_num, result[0]))
            # matrix . append((program_2_tree_num, program_1_tree_num, result))

            print("Finished comparing {} to {}\n".format(
                program_1_tree_num, program_2_tree_num))

    return matrix



if __name__ == "__main__":
    """ Manual and direct comparison of programs. """

    # Set logging level
    loglevel = WARNING   #??????
    basicConfig(level=loglevel, format='%(levelname)s: %(message)s')  #?????
    
    print("Argv: ", sys.argv)

    # Set the program to compare
    if len(sys. argv) < 3: 
        print("Usage : python3 ast_comparison.py <program1> [program2...]")
        print("Requires at least two programs to compare")
        exit(1)

    #sys.argv[file1, file2, file3, ....]  ??????
    #sys.argv kaha se a raha hain and where it declare?
    list_of_programs = sys. argv[1:]     #list_of_programs file

    print(compare_many(list_of_programs))


    #sum    

