import sys
import json
import tokenizer
import re
import time

def parseExpn(tokens):
    if tokens.next() == "(":
        tokens.eat("(")
        e=parseAppl(tokens)
        tokens.eat(")")
        return e
    elif tokens.next() == "L":
        tokens.eat("L")
        name=tokens.eatName()
        tokens.eat(".")
        e=parseAppl(tokens)
        return ["Lambda",name,e]
    elif tokens.nextIsName():
        return ["Variable",tokens.eatName()]

def parseAppl(tokens):
    e=parseExpn(tokens)
    x = tokens.next()
    print(x)
    while x not in (")","eof",""):
        time.sleep(3)
        e=["App",e,parseExpn(tokens)]
        x = tokens.next()
    return e
        
def treeToDOT(tree):
    """
    Converts an AST, passed in, into a graph in DOT format, which it
    then returns as a string. 
    """
    # non-node objects, such as integers, can show up more than once
    # in a given AST. since they each need their own node for rendering
    # reasons, and id(0) == id(0), this is a variable which counts up
    # to give each an unique identifier
    jankID=0 
    def recurse(tree):
        # the non-node id would be better handled by making the
        # DOT formatter a class, but that's a bit too far for a bonus
        # so this, while unfortunate, will have to do:
        nonlocal jankID
        # for each node to render separately, it must have an unique
        # name, as mentioned above. thankfully, id's exact job is
        # associating unique values with objects
        s=f'"node{id(tree)}" [label="{tree[0]}"];\n'
        for i in tree[1:]:
            if isinstance(i,list):
                s+=f'"node{id(tree)}" -> "node{id(i)}";\n'
                s+=recurse(i)
            else:
                s+=f'"node{id(tree)}" -> "JANKY{jankID}";\n'
                s+=f'"JANKY{jankID}" [label="{i}" shape=box];\n'
                jankID+=1
        return s;
    return f"""
digraph AbstractSyntaxTree {{
{recurse(tree)}
}}
"""

def prettyprint(tree):
    if isinstance(tree,list):
        s=tree[0]+"\n"
        for i in tree[1:]: # if there aren't any, this is a base case
            # this regex intelligently indents things
            s+=re.sub("(?m)^(?!$)","    ",prettyprint(i))
        return s
    else:
        return str(tree)+"\n"

def parseAndReport(tks):
    ast = parseAppl(tks)
    tks.checkEOF()  # Check if everything was consumed.
    print()
    print(prettyprint(ast))
    print()
    # TODO: make this work better with loadAll;
    # this is messy not-intended-for-human-consumption output, so
    # dumping it in stdout seems wrong, but so's a fixed file when
    # multiple reported parses can happen
    with open("test.gv",'w') as f:
        f.write(treeToDOT(ast))
    return ast # also, you forgot to do this. ast below would've been None


# the whole kit 'n' kaboodle, only call this if you want to invoke the powers
# of interpreting an AST.
def interpret(ast):
    return "poop"

# this does a single beta reduce step.
# returns a new ast with the beta reduce step done
def betaReduce(ast):
    if ast[0] == "Lambda":
        # first thing's first, gotta alpha rename
        alphaRemaim( ast, betaReduce(ast[1]) )
        
        # reduce subtrees
        a = betaReduce(ast[1])
        b = betaReduce(ast[2])

        #return the new subtree
        return ["Lambda",a,b]
 
    if ast[0] == "App":

        betaReduce(ast[1])
        betaReduce(ast[2])
        # now both sides of the tree have been beta reduced.
        thingThatNeedsToBeApplied = ast[2]

        
        # if left side is a lambda, it gets swaggy
        if ast[1][0] == "Lambda":
            # the thingThatNeedsToBeApplied has to replace all 
            # of the things on the left of Lambda
            thingToReplace = ast[1][1]
            
            # in the second argument of the lambda, gotta replace
            def replace(ast,thingToReplace,replaceWithThis):
                if len(ast) < 1:
                    return ast
                if ast[0] == thingToReplace:
                    ast[0] = replaceWithThis
                for i in ast:
                    replace(ast[i],thingToReplace,replaceWithThis) 
            newTree = replace(ast[1][2], thingToReplace, thingThatNeedsToBeApplied)
            return newTree

        return ["App", ast[1], ast[2]]

    if ast[0] == "Variable":
        return ast[1]
            



# this does all the beta reduce steps.
# retuns the reduced ast
def betaReduceLoop(ast):
    # should check to make sure it isn't beta reducible also!
    newAst = betaReduce(ast)
    if (ast) == newAst:
        # everything is done. I can die happy now (maybe)
        return ast
    betaReduceLoop(newAst)
    
# Renames a specific variable in the current part of the tree. Basically, only
# renames the variables in the current lambda to some weird ass name that won't
# be repeated, ever, probably.
def alphaRemaim(ast, variableName):
    # transverse the ast and rename all of the variables of variableName to
    # some random ass new name. If there's a lambda with the same variable, 
    # no more renaming.
    
    # generate a kick ass new random name
    newKickAssName = variableName + id(ast)
    
    def recursion(ast, oldName):
        if len(ast) < 0:
            return "swagyolo"
        if len(ast) == 1: #in this case, we're looking at a variable
            if ast[0] == variableName:
                ast[0] = newKickAssName
        for i in ast[0:-1]:
            recursion(i,oldName)

    recursion(ast, variableName)


def loadAll(files):
    try:
        # Load definitions from the specified source files.
        for fname in files:
            print("[opening "+fname+"]")
            f = open(fname,"r")
            src = f.read()
            tks = tokenizer.TokenStream(src,filename=fname)
            ast = parseAndReport(tks)
    except tokenizer.SyntaxError as e:
        print("Syntax error.")
        print(e.args[0])
        print("Bailing command-line loading.")
    except tokenizer.ParseError as e:
        print("Failed to consume all the input in the parse.")
        print(e.args[0])
        print("Bailing command-line loading.")
    except tokenizer.LexError as e:
        print("Bad token reached.")
        print(e.args[0])
        print("Bailing command-line loading.")


#
#  usage: 
#    python3 NaFPL.py <file 1> ... <file n>
#
#      - this runs the parser against the specified .ml files
#
if __name__ == "__main__":
    if len(sys.argv) > 1:
        loadAll(sys.argv[1:])
    else:
        print("Enter an expression to parse: ",end='')
        parseAndReport(tokenizer.TokenStream(input()))
