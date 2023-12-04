
from __future__ import annotations
from sympy import Symbol, Not, Expr, Or, And
from sympy.logic.boolalg import simplify_logic, to_dnf, BooleanAtom
import itertools as it
from typing import Dict, List, Set, Optional, Union, Callable, Tuple
from dataclasses import dataclass
import config as cf
import graphviz as gz
import discord as ds
from random import randint

AUTHOR_DICT = {}

# I imagine adding new conditions is most of what people are gonna want to do
# thankfully, it's very easy
# you don't need to understand any of the logic stuff
# your condition must:
# - subclass sympy.Symbol
# - have a prob attribute, that should correspond to the rough 
#   expected chance the condition is met (this is used to optimise the tree)
# - have an eval method like the ones on the classes below, that takes a 
#   ds.Message object as argument 1, the lowercase string of that message's content as argument 2, and returns True or False

# One extra detail. The logic eliminates identical conditions - which we want it to! No sense checking the same thing twice
# However, sometimes you don't want this behaviour. The best example is probably OneIn - one 1 in 6 chance passing does not imply
# other 1-in-6 chances should also pass. To get around this, we just append the object ID to its name. 

class Contains(Symbol):
    def __init__(self, *args):
        super().__init__()
        self.prob=0.1
        self.name = self.name.lower()

    def eval(self, _message: ds.Message, content: str):
        return self.name in content
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Contains: \"" + self.name + "\""

class AuthoredBy(Symbol):
    def __init__(self, *args):
        super().__init__()
        self.prob=0.1
        self.name = self.name

    def eval(self, message: ds.Message, _content: str):
        print(self)
        print(message)
        return self.name == message.author.name
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "AuthoredBy: \"" + self.name + "\""

class OneIn(Symbol):
    def __init__(self, *args):
        super().__init__()
        self.prob=0.1
        try:
            self.die_size = int(self.name)
        except:
            raise TypeError("Die size must be an int")
        
        self.name = self.name + " id:" + str(id(self))

    def eval(self, _message: ds.Message, _content: str):
        return randint(1, self.die_size) == 1
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "OneIn: " + str(self.die_size)

@dataclass
class Response:
    message: str
    author: str

    def __post_init__(self):
        if self.author not in AUTHOR_DICT:
            AUTHOR_DICT[self.author] = cf.DAILY_INVOCATIONS // 4

    def check_respond(self) -> Optional[str]:
        respond = randint(1, cf.DAILY_INVOCATIONS) > AUTHOR_DICT[self.author]
        if respond:
            AUTHOR_DICT[self.author] += 1
            return self.message
        
        return None

@dataclass
class Condition:
    message: Response
    condition: Expr

    def __post_init__(self):
        self.condition = to_dnf(self.condition)
    
def parse_dnf_term(dnf_and_term: And, term: Union[Not, Symbol]) -> Union[And, bool]:
    """Modifies a term of a DNF-form boolalg equation given that a symbol is True. 
    Each term is either false (voids the whole term) or true (can be removed from the term)"""
    
    complement = Not(term) if not isinstance(term, Not) else term.args[0]
    
    for i, arg in enumerate(dnf_and_term.args):
        if arg == term:
            ret_args = dnf_and_term.args[:i] + dnf_and_term.args[1+i:]

            if ret_args:
                return And(*ret_args)
            else:
                return True
        
        elif arg == complement:
            return False
    
    return dnf_and_term

def parse_expression(expression: Union[Or, And, Not, Contains], term: Union[Not, Symbol]) -> Union[Or, bool]:
        new_args = []
        
        # ngl the way sympy automatically collapses 1-member Or objects is kind of annoying
        # means we gotta have this whole type match tree
        # we're haskell now
        match expression:
            case Or():
                for and_term in expression.args:
                    if isinstance(and_term, And):
                        ret = parse_dnf_term(and_term, term)
                    else:
                        complement = Not(term) if not isinstance(term, Not) else term.args[0]
                        
                        if and_term == term:
                            ret = True
                        elif and_term == complement:
                            ret = False
                        else:
                            ret = and_term

                    if ret == True:
                        return True
                    
                    if ret == False: 
                        continue

                    new_args.append(ret)
        
            case And():
                ret = parse_dnf_term(expression, term)

                if ret == True:
                    return True
                    
                if ret == False: 
                    return False

                new_args.append(ret)
            
            case _:
                complement = Not(term) if not isinstance(term, Not) else term.args[0]

                if expression == term:
                    return True
                elif expression == complement:
                    return False
                else:
                    return expression    
    
        if new_args:
            return Or(*new_args)
        
        else:
            return False

@dataclass
class TerminalNode:
    node: Optional[ConditionNode]
    messages: Optional[List[Response]]

    def _add_messages(self, message: ds.Message, content: str, message_list: List) -> None:
        message_list += [reply for message in self.messages if (reply := message.check_respond())]
        
        if self.node:
            self.node._add_messages(message, content, message_list)
    
    def pass_down_next_graph(self, next_graph_head: ConditionNode):
        if self.node:
            self.node.pass_down_next_graph(next_graph_head)
        else:
            self.node = next_graph_head
    
    def _get_graph(self, graph: gz.Digraph):
        label_terms = []

        if self.messages:
            label_terms.append("Messages: " + ", ".join(message.message for message in self.messages))
        
        graph.node(str(id(self)), "\n".join(label_terms))

        strid = str(id(self))

        if self.node:
            node_id = self.node._get_graph(graph)
            graph.edge(strid, node_id)
        
        return strid

@dataclass
class ConditionNode:
    condition: Optional[Contains]
    positivenode: Optional[ConditionNode]
    negativenode: Optional[ConditionNode]
    messages: Optional[List[Response]] = None

    def _add_messages(self, message: ds.Message, content: str, message_list: List) -> None:
        message_list += [reply for message in self.messages if (reply := message.check_respond())]
        print(message_list)

        if self.condition:
            cond_pass = self.condition.eval(message, content)
        else:
            cond_pass = False

        if cond_pass:
            self.positivenode._add_messages(message, content, message_list)
        
        elif not(cond_pass):
            self.negativenode._add_messages(message, content, message_list)
        
    def get_messages(self, message: ds.Message) -> List[str]:
        if self.messages == None:
            raise RuntimeError("Improperly constructed tree, node has messages = None")
        
        message_list = []
        content = message.content.lower()
        self._add_messages(message, content, message_list)

        return message_list

    def get_graph(self):
        graph = gz.Digraph(strict=True, format="jpeg")
        self._get_graph(graph)
        graph.unflatten(4)
        graph.render("/tmp/out")
        pass

    def _get_graph(self, graph: gz.Digraph):
        label_terms = []

        if self.messages:
            label_terms.append("Messages: " + ", ".join(message.message for message in self.messages))

        if self.condition:
            label_terms.append("Condition: " + str(self.condition))
        
        graph.node(str(id(self)), "\n".join(label_terms))

        strid = str(id(self))

        if self.positivenode:
            posnode = self.positivenode._get_graph(graph)
            graph.edge(strid, posnode, label=" True")

        if self.negativenode:
            negnode = self.negativenode._get_graph(graph)
            graph.edge(strid, negnode, label=" False")
        
        return strid

    
    def pass_down_next_graph(self, next_graph_head: ConditionNode) -> None:
        for node_name in ("positivenode", "negativenode"):
            if (node := getattr(self, node_name)):
                if isinstance(node, TerminalNode) and not(node.messages):
                    setattr(self, node_name, next_graph_head)

                node.pass_down_next_graph(next_graph_head)
            else:
                setattr(self, node_name, next_graph_head)

    def __repr__(self) -> str:
        none_or_non_none = lambda x: "None" if x == None else "Non-None"
        return "ConditionNode(condition=" + str(self.condition) + " messages=" + str(self.messages) + " positivenode=" + none_or_non_none(self.positivenode) + " negativenode=" + none_or_non_none(self.negativenode)+")"


def process_conds(conds: List[Condition]) -> ConditionNode:
    cond_connection_map: Dict[frozenset[Symbol], List[Condition]] = {}

    # sympy can only handle at most 8 unique symbols in an equation, because their simplifying
    # method scales hard with that
    # this gets around that by essentially splitting the tree into subtrees

    # if two sets of symbols are completely disconnected, they'll always just be put into separate trees
    # because that just makes the tree smaller and simpler

    # if a valid network of interconnected symbols has more than 8 components
    # things get complicated
    # we find the least bad way to split the set, repeating the fewest possible number of elements
    for cond in conds:
        condslist = cond.condition.free_symbols

        if len(condslist) > cf.MAX_TREE_HEIGHT:
            # if someone puts a single condition that by itself makes an illegally large tree
            # exclude it
            # eventually implement banning them from the server
            continue

        matches = [present_symbols for present_symbols in cond_connection_map if any(symbol in present_symbols for symbol in condslist)]
        
        new_key = frozenset(it.chain(condslist, *matches))

        new_value = list(it.chain([cond], *(cond_connection_map[match] for match in matches)))

        for match in matches:
            del cond_connection_map[match]
        
        cond_connection_map[new_key] = new_value
    
    list_of_disjoint_groups = []

    for key, grouped_conds in cond_connection_map.items():
        newly_created_kvs: Dict[frozenset[Symbol], List[Condition]] = {}
        
        while len(key) > cf.MAX_TREE_HEIGHT:
            # if we're here that means we constructed a tree that's larger than allowed
            # that kinda sucks, because the individual components are okay
            # so we can't just throw them away

            lowest_connection = None

            for i, cond in enumerate(grouped_conds):
                other_conds = grouped_conds[:i] + grouped_conds[i+1:]

                connection_sum = sum(sum(1 for j in other_cond.condition.free_symbols if j in cond.condition.free_symbols) for other_cond in other_conds)

                if lowest_connection == None or connection_sum < lowest_connection: 
                    least_connected = cond
                    lowest_connection = connection_sum
                    least_connected_other_conds = other_conds
            
            # subtract the least connected key from the other keys
            key = frozenset(it.chain(*(cond.condition.free_symbols for cond in least_connected_other_conds)))
            grouped_conds = least_connected_other_conds 

            least_connected_symbols = frozenset(least_connected.condition.free_symbols)
            
            add_new = True
            
            for key in newly_created_kvs:
                combined_set = frozenset(it.chain(least_connected_symbols, key))
                
                if len(combined_set) <= cf.MAX_TREE_HEIGHT:
                    newly_created_kvs[combined_set] = newly_created_kvs[key] + [least_connected]
                    del newly_created_kvs[key]
                    add_new = False

                    break
            
            if add_new:
                newly_created_kvs[least_connected_symbols] = [least_connected]
        
        list_of_disjoint_groups.append(grouped_conds)
        list_of_disjoint_groups += [v for v in newly_created_kvs.values()]

    # this function is the heart of tree construction
    def rec_cond_crawler(expression_list: List[Condition], lowest_cost: Optional[int] = None) -> Tuple[float, Optional[ConditionNode]]:
        # if you're here, it means there are no more conditions to try and meet. Make a terminal node
        if not expression_list:
            return (0, TerminalNode(None, None))

        # this is a list of every unique symbol at this layer
        # symbols are the atoms of the logic here - does a string contain a given word, etc. etc.
        condslist = list({free_symb for term in expression_list for free_symb in term.condition.free_symbols})

        costlist = []

        for cond in condslist:
            expression_list_pos = [Condition(expression.message, parse_expression(expression.condition, cond)) for expression in expression_list]
            
            notcond = Not(cond)
            expression_list_neg = [Condition(expression.message, parse_expression(expression.condition, notcond)) for expression in expression_list]

            true_branch_cost, true_path = rec_cond_crawler([expr for expr in expression_list_pos if not isinstance(expr.condition, BooleanAtom)])
            false_branch_cost, false_path = rec_cond_crawler([expr for expr in expression_list_neg if not isinstance(expr.condition, BooleanAtom)])
        
            # right now we just assume all conditions have equal cost
            cost = cond.prob * true_branch_cost + (1-cond.prob) * false_branch_cost + 1

            if true_path:
                true_path.messages = [expr.message for expr in expression_list_pos if expr.condition == True] 
            
            if false_path:
                false_path.messages = [expr.message for expr in expression_list_neg if expr.condition == True] if false_path else None

            path_obj = ConditionNode(cond, true_path, false_path)

            costlist.append((cost, path_obj))

        cheapest = min(costlist, key=lambda x: x[0])

        return cheapest
    
    val_iter = iter(list_of_disjoint_groups)

    first_graph = next(val_iter, None)

    if not first_graph:
        return None

    # construct the tree for the first independent network
    _, ret = rec_cond_crawler(first_graph)
    ret.messages = []
    last_head = ret

    # for each additional tree, create it attached to the tree before it
    # to make a treetree
    
    for independent_graph in val_iter:
        _, additional_head = rec_cond_crawler(independent_graph)
        additional_head.messages = []
        last_head.pass_down_next_graph(additional_head)
        last_head = additional_head

    return ret


