import sys

import lrparsing
from lrparsing import Keyword, List, Prio, Ref, THIS, Token, Tokens
from declarative_tree import Contains, OneIn, Condition, AuthoredBy, ContainsWord
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
    onein = Keyword("onein") + (T.integer | (":" + T.integer))
    contains = Keyword("contains") + (T.string | (":" + T.string))
    authoredby = Keyword("authoredby") + (T.string | (":" + T.string))
    containsword = Keyword("containsword") + (T.string | (":" + T.string))

    condition = onein | contains | authoredby | containsword
    
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
            ret = tup[2][1] if tup[2][1] != ":" else tup[3][1]
            return OneIn(ret)
        
        case "contains":
            string = tup[2][1] if tup[2][1] != ":" else tup[3][1]
            string = string[1:-1]
            return Contains(string)
        
        case "containsword":
            string = tup[2][1] if tup[2][1] != ":" else tup[3][1]
            string = string[1:-1]
            return ContainsWord(string)
        
        case "authoredby":
            string = tup[2][1] if tup[2][1] != ":" else tup[3][1]
            string = string[1:-1]
            return AuthoredBy(string)
        
        case "or_list":
            return Or(*(rec_symp_crawler(i) for i in tup[1:] if not i[0].name == "'|'"))
        
        case "and_list":
            ret = tuple(rec_symp_crawler(i) for i in tup[1:] if not i[0].name == "'&'")
            return And(*ret)

        case "sub_bool":
            return rec_symp_crawler(tup[2])
        
        case "not_term":
            return Not(rec_symp_crawler(tup[2]))
        
        case _:
            return rec_symp_crawler(tup[1])
        
def parse_string(string: str) -> Condition:
    parse_tree = ExprParser.parse(string)
    ret = rec_symp_crawler(parse_tree)
    return ret

if __name__=="__main__":
    # test = ExprParser.parse("contains: \"foo\" & contains \"bar\" & contains \"Darren\" & ~contains \"Fish\"")
    # bar = rec_symp_crawler(test)

    # foo = ExprParser.parse('contains: "darren"')
    bar = ExprParser.parse('(contains: "woman" | contains: "lady") & (contains: "big" | contains: "large" | contains: "giant" | contains: "huge")')
    barr = rec_symp_crawler(bar)
    breakpoint()