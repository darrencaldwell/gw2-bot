from random import choice
from tomli import load
import typing as t

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


if __name__ == "__main__":
    foo = personality_replace("{greeting}", "burning_hate")
    print(foo)
