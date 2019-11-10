import sys
import json
import tokenizer
import re
import time
import copy

DEBUG_COMMENTS_ON = False
DEBUG_FILE_WRITING_ON = False

def parseMacros(tokens):
    defns=[]
    while tokens.next()=="[":
        tokens.eat("[")
        name=tokens.eatName()
        tokens.eat("=")
        defn=parseAppl(tokens)
        tokens.eat("]")
        defns.append((name,defn))
    base=parseAppl(tokens)
    for name,defn in defns[::-1]:
        base=["App",["Lambda",name,base],defn]
    return base

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
    while x not in (")","eof","]",""):
        time.sleep(0.1)
        e=["App",e,parseExpn(tokens)]
        x = tokens.next()
    return e
        
def treeToDOT(*trees):
    """
    Converts ASTs, passed in, into a graph in DOT format, which it
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
        # things can get hella long. this is truncator:
        def trunc(s):
            if len(s)<20:
                return s
            else:
                return f"{s[:5]}[...]{s[-15:]}"
        # for each node to render separately, it must have an unique
        # name, as mentioned above. thankfully, id's exact job is
        # associating unique values with objects
        s=f'"node{id(tree)}" [label="{trunc(tree[0])}"];\n'
        for i in tree[1:]:
            if isinstance(i,list):
                s+=f'"node{id(tree)}" -> "node{id(i)}";\n'
                s+=recurse(i)
            else:
                s+=f'"node{id(tree)}" -> "JANKY{jankID}";\n'
                s+=f'"JANKY{jankID}" [label="{trunc(i)}" shape=box];\n'
                jankID+=1
        return s;
    return f"""
digraph AbstractSyntaxTree {{
{'''
'''.join(map(recurse,trees))}
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
    ast = parseMacros(tks)
    tks.checkEOF()  # Check if everything was consumed.
    print()
    print(prettyprint(ast))
    print()
    print(unparse(ast))
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
    return betaReduceLoop(ast)

# this does a single beta reduce step.
# returns a new ast with the beta reduce step done
def betaReduce(ast):
    if DEBUG_COMMENTS_ON:
        print(ast,"is getting beta reduced! yeet")
    if not ast:
        if DEBUG_COMMENTS_ON:
            print("!!!",ast)
        return 
    if ast[0] == "Lambda":
        # first thing's first, gotta alpha rename
        if DEBUG_COMMENTS_ON:
            print(ast,"is the ast before we remaim")
            print(ast[1], "is the variable that willl be remaimed")

        #rename the ast[1]s in the ast
        alphaRemaim( ast, ast[1] )
        
        # reduce subtrees
        a = betaReduce(ast[1])
        b = betaReduce(ast[2])

        #return the new subtree
        return ["Lambda",a,b]
 
    if ast[0] == "App":
        if DEBUG_COMMENTS_ON:
            print("BETA REDUCING THE LEFT \n")
        left = betaReduce(ast[1])

        if DEBUG_COMMENTS_ON:
            print("BETA REDUCINT THE RIGHT\n")
        right = betaReduce(ast[2])
        # now both sides of the tree have been beta reduced.
        thingThatNeedsToBeApplied = right

        
        # if left side is a lambda, it gets swaggy
        if ast[1][0] == "Lambda":
            # the thingThatNeedsToBeApplied has to replace all 
            # of the things on the left of Lambda
            thingToReplace = ast[1][1]
            
            # in the second argument of the lambda, gotta replace
            def replace(ast,thingToReplace,replaceWithThis):
                # first replace the variable if it needs to be replaced
                if DEBUG_COMMENTS_ON:
                    print("REPLACIN:",ast,thingToReplace,replaceWithThis)
                if ast[0] == "Variable":
                    if ast[1] == thingToReplace:
                        ## Note to Ariel: I made it replace the variable object instead
                        # of the string in it. It was rather simple, except

#                       ast[1] = replaceWithThis
#                       if isinstance(ast,list):
#                           ast = replace(ast, thingToReplace ,replaceWithThis)
#                       else:
#                           ast = [replaceWithThis]

                        ## Note: the deepcopy is needed because the same-memory-address
                        # thing caused variable objects to be shared and over-maimed as each of their
                        # parent lambdas was maimed.
                        return copy.deepcopy(replaceWithThis)
                # return if we're at an dead end
                if len(ast) <= 1 or not isinstance(ast,list):
                    if DEBUG_COMMENTS_ON:
                        print("ast is short!",ast)
                    return ast

                #continue on for all subtrees
                for i in range(len(ast)):
                    ## Note: Mutating the list here as opposed to in the function
                    # ended up easier
                    ast[i]=replace(ast[i],thingToReplace,replaceWithThis) 
                return ast
            
            if DEBUG_COMMENTS_ON:
                print("old tree is ", ast[1][2])
                print("thing to replace is",thingToReplace)
                print("thingThatNeedsToBeApplied is ",thingThatNeedsToBeApplied)
            
            newTree = replace(ast[1][2], thingToReplace, thingThatNeedsToBeApplied)
            
            if DEBUG_COMMENTS_ON:
                print("here's what the new tree is", ast[1][2][1])
                print("actually, it'''s",newTree)
            return newTree

        return ["App", left, right]

    
    return ast
            

if DEBUG_FILE_WRITING_ON:
    stepcount=0

# this does all the beta reduce steps.
# retuns the reduced ast
def betaReduceLoop(ast):
    if DEBUG_FILE_WRITING_ON:
        global stepcount
    # should check to make sure it isn't beta reducible also!
    newAst = betaReduce(ast)
    if DEBUG_COMMENTS_ON:
        print("Reducened!" ,ast,"->", newAst)
    if DEBUG_FILE_WRITING_ON:
        with open(f"beta{stepcount}.gv",'w') as f:
            f.write(treeToDOT(ast))
        stepcount+=1

    if (ast) == newAst:
        # everything is done. I can die happy now (maybe)
        return ast
    return betaReduceLoop(newAst)


# Renames a specific variable in the current part of the tree. Basically, only
# renames the variables in the current lambda to some weird ass name that won't
# be repeated, ever, probably.
def alphaRemaim(ast, variableName):
    # transverse the ast and rename all of the variables of variableName to
    # some random ass new name. If there's a lambda with the same variable, 
    # no more renaming.
    
    # generate a kick ass new random name
    newKickAssName = variableName +"_"+ str(id(ast))
    top=id(ast)
    if DEBUG_COMMENTS_ON:
        print(ast, "is the ast before we remaim!" )
    def recursion(ast, oldName):
        if DEBUG_COMMENTS_ON:       
            print("going through and renaming",oldName,"to",newKickAssName,"in",ast)        
        
        if ast[0] == 'Variable': #in this case, we're looking at a variable
            if ast[1] == oldName:
                if DEBUG_COMMENTS_ON:
        
                    print(ast[1],"is the variable")
                    print(ast,"is the tree")
                    print("it shalt now be:",newKickAssName)
                ast[1] = newKickAssName
        
        if DEBUG_COMMENTS_ON:
            print("here's the ast:",ast)
        if len(ast) <= 1:
            return "swagyolo"

        # don't go into a lambda whose variable is shadowing this one's
        if ast[0]=="Lambda" and ast[1] == oldName and id(ast)!=top:
            if DEBUG_COMMENTS_ON:
                print("cave johnson we're done here",ast)   
            return
        
        if isinstance(ast,list):
            for i in range(len(ast)):
                # GET OUT OF HERE YOU FREAKING OLD NAMES!!
                if ast[i] == oldName:
                    ast[i] = newKickAssName 

                #lets do the rest of the ast now
                recursion(ast[i],oldName)
        #'''
    recursion(ast, variableName)

    if ast[0]=="Lambda": # should always hold
        ast[1]=newKickAssName
    else:
        if DEBUG_COMMENTS_ON: # gotta stay safe with these print statements!
            print(ast,"why is this like this")

# demaims a name
def basename(name):
    return name.split("_")[0]

# demaims an entire AST, bc the maiming level on the maths is ridiculous
def demaim(ast):
    def varnames(ast):
        if isinstance(ast,str):
            return {ast}
        vars=set()
        for i in ast:
            vars |= varnames(i)
        return vars
    def applyRemaps(ast):
        if ast[0]=="Variable":
            return ["Variable", remaps.get(ast[1],ast[1])]
        elif ast[0]=="App":
            return ["App",applyRemaps(ast[1]),applyRemaps(ast[2])]
        elif ast[0]=="Lambda":
            return ["Lambda",remaps.get(ast[1],ast[1]),applyRemaps(ast[2])]
            
    vars=varnames(ast)
    bases={}
    for i in vars:
        bases[basename(i)]=bases.get(basename(i),[])+[i]
    remaps={}
    for i in bases:
        for j in range(len(bases[i])):
            if len(bases[i])==1:
                remaps[bases[i][j]]=basename(bases[i][j])
            else:
                remaps[bases[i][j]]=basename(bases[i][j])+"_"+str(j)
    return applyRemaps(ast)
    

# Goes from an AST back to syntax.
def unparse(ast):
    # awful case-statement hack but eh
    lookup={
        "Lambda": lambda x,y: f"(L{x}.{unparse(y)})",
        "App": lambda x,y: f"{unparse(x)} ({unparse(y)})" if y[0]=="App" else f"{unparse(x)} {unparse(y)}",
        "Variable": lambda x: x
    }
    return lookup[ast[0]](*ast[1:])

def loadAll(files):
    try:
        # Load definitions from the specified source files.
        for fname in files:
            print("[opening "+fname+"]")
            f = open(fname,"r")
            src = f.read()
            tks = tokenizer.TokenStream(src,filename=fname)
            ast = parseAndReport(tks)
            reduced = demaim(interpret(ast))
            print(reduced)
            print()
            print(prettyprint(reduced))
            print()
            print(unparse(reduced))
            print()
            with open("reduced.gv",'w') as f:
                f.write(treeToDOT(reduced))
            
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
        yolo = parseAndReport(tokenizer.TokenStream(input()))
        reduced = demaim(interpret(yolo))
        print(reduced)
        print()
        print(prettyprint(reduced))
        print()
        print(unparse(reduced))
        print()
        with open("reduced.gv",'w') as f:
            f.write(treeToDOT(reduced))
