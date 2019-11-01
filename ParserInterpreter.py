from sys import argv
import json

def parseExpn(tokens):
    if tokens.next() == "(":
        tokens.eat("(")
        e=parseAppl(tokens)
        tokens.eat(")")
        return e
    elif tokens.next() == "L":
        name=tokens.eatName()
        tokens.eat(".")
        e=parseAppl(tokens)
        return ["Lambda",name,e]
    elif tokens.nextIsName():
        return ["Variable",tokens.eatName()]

def parseAppl(tokens):
    e=parseExpn(tokens)
    while tokens.next() not in (")","eof"):
        e=["App",e,parseExpn(tokens)]
    return e
        
