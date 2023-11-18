
from __future__ import annotations
from sympy import Symbol, Not, Expr, Or, And
from sympy.logic.boolalg import simplify_logic, to_dnf, BooleanAtom
import itertools as it
from typing import Dict, List, Set, Optional, Union, Callable, Tuple
from dataclasses import dataclass
import config as cf

class Contains(Symbol):
    def __init__(self, *args):
        super().__init__()
        self.prob=0.1
        self.name = self.name.lower()

    def eval(self, string):
        return self.name in string
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Contains: " + super().__repr__()

@dataclass
class Condition:
    message: str
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
class ConditionNode:
    condition: Optional[Contains]
    positivenode: Optional[ConditionNode]
    negativenode: Optional[ConditionNode]
    messages: Optional[List] = None

    def _add_messages(self, string: str, message_list: List) -> None:
        for message in self.messages:
            message_list.append(message)
        
        if self.condition:
            cond_pass = self.condition.eval(string)
        else:
            cond_pass = False

        if cond_pass and self.positivenode:
            self.positivenode._add_messages(string, message_list)
        
        elif not(cond_pass) and self.negativenode:
            self.negativenode._add_messages(string, message_list)
        
    def get_messages(self, string: str) -> List[str]:
        if self.messages == None:
            raise RuntimeError("Improperly constructed tree, node has messages = None")
        
        message_list = []
        string = string.lower()
        self._add_messages(string, message_list)

        return message_list
    
    def pass_down_next_graph(self, next_graph_head: ConditionNode) -> None:
        for node_name in ("positivenode", "negativenode"):
            if (node := getattr(self, node_name)):
                node.pass_down_next_graph(next_graph_head)
            else:
                setattr(self, node_name, next_graph_head)

    def __repr__(self) -> str:
        none_or_non_none = lambda x: "None" if x == None else "Non-None"
        return "ConditionNode(condition=" + str(self.condition) + " messages=" + str(self.messages) + " positivenode=" + none_or_non_none(self.positivenode) + " negativenode=" + none_or_non_none(self.negativenode)+")"


def process_conds(conds: List[Condition]) -> ConditionNode:
    cond_connection_map: Dict[frozenset[Symbol], List[Condition]] = {}

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

            closeness_map: Dict[int, List[Tuple[Condition, List[Condition]]]] = {}

            for i, cond in enumerate(grouped_conds):
                other_conds = grouped_conds[:i] + grouped_conds[i+1:]

                closeness_sum = sum(sum(1 for j in other_cond.condition.free_symbols if j in cond.condition.free_symbols) for other_cond in other_conds)

                closeness_map[closeness_sum] = closeness_map.get(closeness_sum, []) + [(cond, other_conds)]
            
            least_connected, other_conds = closeness_map[min(closeness_map.keys())][0]

            # subtract the least connected key from the other keys
            key = frozenset(it.chain(*(cond.condition.free_symbols for cond in other_conds)))
            grouped_conds = other_conds 

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

    def rec_cond_crawler(expression_list: List[Condition], lowest_cost: Optional[int] = None) -> Tuple[float, Optional[ConditionNode]]:
        if not expression_list:
            return (0, ConditionNode(None, None, None))

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

    _, ret = rec_cond_crawler(first_graph)
    ret.messages = []
    last_head = ret
    
    for independent_graph in val_iter:
        _, additional_head = rec_cond_crawler(independent_graph)
        additional_head.messages = []
        last_head.pass_down_next_graph(additional_head)
        last_head = additional_head

    return ret