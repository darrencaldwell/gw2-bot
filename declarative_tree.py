
from __future__ import annotations
from sympy import Symbol, Not, Expr, Or, And
from sympy.logic.boolalg import simplify_logic, to_dnf
import itertools
from typing import Dict, List, Set, Optional, Union, Callable

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

subcond1 = Contains("darren")
subcond2 = Contains("piss")
subcond3 = Contains("caithe")
subcond4 = Contains("piston")
subcond5 = Contains("werewolf")

cond1 = subcond1 & subcond2 & ~subcond3
cond2 = subcond1 & ~subcond2 & subcond3
cond3 = subcond1 & ~subcond2 & ~subcond3

cond4 = (subcond1 | subcond2) & subcond3
cond5 = (subcond1 | subcond2) & subcond4
cond6 = (subcond1 | subcond2) & subcond5

conds = [subcond1, subcond2, subcond3, subcond4, subcond5]

def parse_dnf_term(dnf_and_term: And, term: Union[Not, Symbol]) -> Union[And, bool]:
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

def parse_expression(expression: Or, term: Union[Not, Symbol]) -> Union[Or, bool]:
        new_args = []

        if expression == [subcond1, subcond1 & subcond5, subcond3 & subcond1]:
            breakpoint()
        
        if isinstance(expression, Or):
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
        
        elif isinstance(expression, And):
            ret = parse_dnf_term(expression, term)

            if ret == True:
                return True
                
            if ret == False: 
                return False

            new_args.append(ret)
            
        else:
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



def process_conds(conds):
    condslist = list({term for symbol in conds for term in symbol.free_symbols})

    dnf_list = [to_dnf(cond) for cond in conds]
    
    def rec_cond_crawler(expression_list: List[Or], path: Optional[List] = None, lowest_cost: Optional[int] = None):
        if not expression_list:
            return (0, path)
        
        condslist = list({free_symb for term in expression_list for free_symb in term.free_symbols})

        costlist = []

        for cond in condslist:
            tpath = path + [cond] if path else [cond]
            fpath = path + [Not(cond)] if path else [Not(cond)]
            
            expression_list_pos = [parse_expression(expression, cond) for expression in expression_list]
            
            notcond = Not(cond)
            expression_list_neg = [parse_expression(expression, notcond) for expression in expression_list]

            # if (not [expr for expr in expression_list_pos if not isinstance(expr, bool)]) or (not [expr for expr in expression_list_neg if not isinstance(expr, bool)]):
            #     breakpoint()

            true_branch_cost, true_path = rec_cond_crawler([expr for expr in expression_list_pos if not isinstance(expr, bool)], tpath)
            false_branch_cost, false_path = rec_cond_crawler([expr for expr in expression_list_neg if not isinstance(expr, bool)], fpath)
        
            cost = cond.prob * true_branch_cost + (1-cond.prob) * false_branch_cost + 1

            costlist.append((cost, (true_path, false_path)))

        foo = min(costlist, key=lambda x: x[0])

        return foo

    return rec_cond_crawler(dnf_list)

foo = parse_expression(subcond1, Not(subcond1))

zub = process_conds([ cond5, cond6, cond4,])

class ConditionNode:
    def __init__(self, condition: Callable[[str], bool], positivenode: Optional[ConditionNode], negativenode: Optional[ConditionNode]):
        self.condition = condition
        self.positivenode = positivenode
        self.negativenode = negativenode


    def add_messages(self, string: str, message_list: Optional[List] = None):
        if not message_list:
            message_list = []
        
        
            
            

foo = ConditionNode(lambda x: x, None, None)



# def get_dependency(expr):
#     expr_free_symbols = expr.free_symbols

#     return {
#         symbol: {
#             "pos": {x for x in simplify_logic(expr & symbol).free_symbols if x != symbol}, 
#             "neg": {x for x in simplify_logic(expr & ~symbol).free_symbols if x != symbol}
#         } 
#     for symbol in expr_free_symbols}

          
# dep1 = get_dependency(cond1)
# dep2 = get_dependency(cond2)
# dep3 = get_dependency(cond3)

# dep4 = get_dependency(cond4)
# dep5 = get_dependency(cond5)
# dep6 = get_dependency(cond6)

# breakpoint()
# def find_common_dependencies(*dependencies: Dict):
#     def get_2_nested(dic, key, posneg):
#         if key in dic:
#             return dic[key][posneg]
#         else:
#             return {}
        
#     return {
#         symbol: {
#             "pos": {x for dependency in dependencies for x in get_2_nested(dependency, symbol, "pos")},
#             "neg": {x for dependency in dependencies for x in get_2_nested(dependency,symbol, "neg")},
#         }
#     for symbol in {key for dependency in dependencies for key in dependency}
#     }
    
# comm = find_common_dependencies(dep1, dep2, dep3)
# comm2 = find_common_dependencies(dep4, dep5, dep6)