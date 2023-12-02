import sys

import lrparsing
from lrparsing import Keyword, List, Prio, Ref, THIS, Token, Tokens
from declarative_tree import Contains, OneIn, Condition
from sympy import Or, And, Not

from typing import Tuple

# use like 
# parse_tree = ExprParser.parse("Contains \"foo\" & Contains \"bar\" & Contains \"Darren\" & ~Contains \"Fish\"")
# rec_symp_crawler(parse_tree)

class ExprParser(lrparsing.Grammar):
    class T(lrparsing.TokenRegistry):
        integer = Token(re="[0-9]+")
        catch = Token(re="[A-Za-z_][A-Za-z_0-9]*")
        string = Token(re="\"(.*?)\"")

    expr = Ref("expr")
    onein = Keyword("OneIn") + T.integer
    contains = Keyword("Contains") + T.string

    condition = onein | contains
    
    or_list = List(expr, "|", min=2)
    and_list = List(expr, "&", min=2)
    
    sub_bool = "(" + (and_list | or_list) + ")" 

    not_term = "~" + (condition | sub_bool)
    
    expr = Prio(        
        condition,  
        not_term,           
        sub_bool,
    )
    
    START = expr | or_list | and_list                   

def rec_symp_crawler(tup: Tuple) -> Condition:
    match tup[0].name:
        case "onein":
            return OneIn(tup[2][1])
        
        case "contains":
            string = tup[2][1][1:-1]
            return Contains(string)
        
        case "or_list":
            return Or(*(rec_symp_crawler(i) for i in tup[1:] if not i[0].name == "'|'"))
        
        case "and_list":
            ret = tuple(rec_symp_crawler(i) for i in tup[1:] if not i[0].name == "'&'")
            return And(*ret)
        
        case "not_term":
            return Not(rec_symp_crawler(tup[2]))
        
        case _:
            return rec_symp_crawler(tup[1])
        
def parse_string(string: str) -> Condition:
    parse_tree = ExprParser.parse(string)
    return rec_symp_crawler(parse_tree)