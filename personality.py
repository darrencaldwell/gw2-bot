from random import choice
from tomli import load
import typing as t

from storage import LockingPandasRWer
from dataclasses import dataclass

with open("personality.toml", "rb") as f:
    personality_toml = load(f)

def personality_replace(string: str, personality: t.Literal["nice", "neutral", "burning_hate"]) -> str:
    iterstr = iter(string)

    ret = ""

    for char in iterstr:
        if char == "{":
            contents = ""
            unmatched = True
            for subchar in iterstr:
                if subchar == "}":
                    ret += choice(personality_toml[personality][contents])
                    unmatched = False
                    break

                else:
                    contents += subchar

            if unmatched:
                raise ValueError('Unmatched "{"')

        else:
            ret += char

    if ret == string:
        return ret
    
    else:
        return personality_replace(ret, personality)

@dataclass
class ColumnDefn:
    name: str
    default: str
    others: list[str]

    @property
    def all(self):
        return [self.default] + self.others

column_defns = [
    ColumnDefn("personality", "neutral", ["nice", "burning_hate"])
]

columns = {column_defn.name: column_defn for column_defn in column_defns}

user_data = LockingPandasRWer("user_data.csv", [column for column in columns])

def sentence_case(string: str):
    to_upper = True

    ret = ""

    for char in string:
        if to_upper and char.isalpha():
            char = char.upper()
            to_upper = False
        
        elif char == ".":
            to_upper = True
        
        ret += char
    
    return ret
             


async def modify(string: str, user_id: int):
    async with user_data.read as dataframe:
        if user_id in dataframe.index:
            personality = dataframe.loc[user_id]["personality"]
        else:
            personality = "neutral"

    replaced = personality_replace(string, personality)

    return sentence_case(replaced)

async def amend(usr: int, **kwargs: str):
    kwargs = {k: v for k, v in kwargs.items() if k in columns and v in columns[k].all}

    if kwargs:
        async with user_data.edit as dataframe:
            if usr in dataframe.index:
                dataframe.loc[usr].update(kwargs)
            else:
                kwargs = {k: kwargs.get(k, v.default) for k, v in columns.items()}
                dataframe.loc[usr] = kwargs
        
        return True
    
    else:
        return False

async def get_user(usr: int):
    async with user_data.read as dataframe:
        return dataframe.loc[usr]
