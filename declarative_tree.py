
from __future__ import annotations
from sympy import Symbol, Not, Expr, Or, And
from sympy.logic.boolalg import simplify_logic, to_dnf, BooleanAtom
import itertools
from typing import Dict, List, Set, Optional, Union, Callable, Tuple
from dataclasses import dataclass

class Contains(Symbol):
    def __init__(self, *args):
        super().__init__()
        self.prob=0.1

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
    condition: Optional[Condition]
    positivenode: Optional[ConditionNode]
    negativenode: Optional[ConditionNode]
    messages: Optional[List] = None

    def _add_messages(self, string: str, message_list: List) -> None:
        for message in self.messages:
            message_list.append(message)
        
        if self.condition:
            cond_pass = self.condition.eval(string)

            if cond_pass and self.positivenode:
                self.positivenode._add_messages(string, message_list)
            
            elif not(cond_pass) and self.negativenode:
                self.negativenode._add_messages(string, message_list)
        
    def get_messages(self, string: str) -> List[str]:
        if self.messages == None:
            raise RuntimeError("Improperly constructed tree, node has messages = None")
        
        message_list = []
        self._add_messages(string, message_list)

        return message_list


def process_conds(conds: List[Condition]) -> ConditionNode:
    def rec_cond_crawler(expression_list: List[Condition], lowest_cost: Optional[int] = None) -> Tuple[float, Optional[ConditionNode]]:
        if not expression_list:
            return (0, ConditionNode(None, None, None))
        
        try:
            condslist = list({free_symb for term in expression_list for free_symb in term.condition.free_symbols})
        except:
            breakpoint()

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

    _, ret = rec_cond_crawler(conds)
    ret.messages = []

    return ret


if __name__ == "__main__":
    subcond1 = Contains("darren")
    subcond2 = Contains("piss")
    subcond3 = Contains("caithe")
    subcond4 = Contains("werewolf")
    subcond5 = Contains("bees")

    cond1 = Condition("caithe", (subcond1 | subcond2) & subcond3)
    cond2 = Condition("werewolf", (subcond1 | subcond2) & subcond4)
    cond3 = Condition("bees", (subcond1 | subcond2) & subcond5)

    tree = process_conds([cond1, cond2, cond3])

    tree.get_messages("darren caithe")