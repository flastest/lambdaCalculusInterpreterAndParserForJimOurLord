import io
import tokenize

DELIMITERS = '()[].L=' # this is hacky, but by doing this, Lx and such work
OPERATORS = ''
WHITESPACE = '\t\n\x0b\x0c\r\x1c\x1d\x1e\x1f \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'


# this is stolen from Jim's code, but changed a little. Thanks, Jim!
class ParseError(Exception):
    pass

class SyntaxError(Exception):
    pass

class LexError(Exception):
    pass




class TokenStream:
    
    def __init__(self,src,filename="STDIN"):
        """
        Builds a new TokenStream object from a source code string.
        """
        self.sourcename = filename
        self.source = src # The char sequence that gets 'chomped' by the lexical analyzer.
        self.tokens = []  # The list of tokens constructed by the lexical analyzer.
        self.extents = []     
        self.starts = []
        self.parendepth=0
        self.cannewline=True

        # Sets up and then runs the lexical analyzer.
        self.initIssue()
        self.analyze()
        self.tokens.append("eof")

    #
    # PARSING helper functions
    #

    def lexassert(self,c):
        if not c:
            self.raiseLex("Unrecognized character.")

    def raiseLex(self,msg):
        s = self.sourcename + " line "+str(self.line)+" column "+str(self.column)
        s += ": " + msg
        raise LexError(s)

    def next(self):
        """
        Returns the unchomped token at the front of the stream of tokens.
        """
        return self.tokens[0]

    def advance(self):
        """ 
        Advances the token stream to the next token, giving back the
        one at the front.
        """
        tk = self.next()
        del self.tokens[0]
        del self.starts[0]
        return tk

    def report(self):
        """ 
        Helper function used to report the location of errors in the 
        source code.
        """
        lnum = self.starts[0][0]
        cnum = self.starts[0][1]
        return self.sourcename + " line "+str(lnum)+" column "+str(cnum)

    def eat(self,tk):
        """
        Eats a specified token, making sure that it is the next token
        in the stream.
        """
        if tk == self.next():
            return self.advance()
        else:
            where = self.report()
            err1 = "Unexpected token at "+where+". "
            err2 = "Saw: '"+self.next()+"'. "
            err3 = "Expected: '"+tk+"'. "
            raise SyntaxError(err1 + err2 + err3)

    def eatName(self):
        """
        Eats a name token, making sure that such a token is next in the stream.
        """
        if self.nextIsName():
            return self.advance()
        else:
            where = self.report()
            err1 = "Unexpected token at "+where+". "
            err2 = "Saw: '"+self.next()+"'. "
            err3 = "Expected a name. "
            raise SyntaxError(err1 + err2 + err3)

    def checkEOF(self):
        """
        Checks if next token is an integer literal token.
        """
        if self.next() != 'eof':
            raise ParseError("Parsing failed to consume tokens "+str(self.tokens[:-1])+".")


    def nextIsName(self):
        """
        Checks if next token is a name.
        """
        tk = self.next()
        isname = tk[0] not in DELIMITERS+OPERATORS+WHITESPACE
        for c in tk[1:]:
            isname = isname and c not in DELIMITERS+OPERATORS+WHITESPACE
        return isname

    
    #
    # TOKENIZER helper functions
    #
    # These are used by the 'analysis' method defined below them.
    #
    # The parsing functions EAT the token stream, whereas
    # the lexcial analysis functions CHOMP the source text
    # and ISSUE the individual tokens that form the stream.
    #

    def initIssue(self):
        self.line = 1
        self.column = 1
        self.markIssue()

    def markIssue(self):
        self.mark = (self.line,self.column)

    def issue(self,token):
        self.tokens.append(token)
        self.starts.append(self.mark)
        self.markIssue()

    def nxt(self,lookahead=1):
        if len(self.source) == 0:
            return ''
        else:
            return self.source[lookahead-1]

    def chompWord(self):
        #self.lexassert(self.nxt().isalpha() or self.nxt() == '_')
        self.lexassert(self.nxt() not in DELIMITERS+OPERATORS+WHITESPACE)
        token = self.chompChar()
        while self.nxt() not in DELIMITERS+OPERATORS+WHITESPACE:
        #self.nxt().isalnum() or self.nxt() == '_':
            token += self.chompChar()
        self.issue(token)            
    
    def chompComment(self):
        self.lexassert(len(self.source)>1 and self.source[0:2] == '(*')
        self.chompChar() # eat (*
        self.chompChar() #
#       print("comment",end="")
        while len(self.source) >= 2 and self.source[0:2] != '*)':        
            self.chomp()
 #          print("!",end="")
        if len(self.source) < 2:
            self.raiseLex("EOF encountered within comment")
        else:
            self.chompChar() # eat *)
            self.chompChar() #
#       print()

    def chomp(self):
        if self.nxt() in WHITESPACE:
            self.chompWhitespace()
        else:
            self.chompChar()

    def chompChar(self):
        self.lexassert(len(self.source) > 0)
        c = self.source[0]
        self.source = self.source[1:]
        self.column += 1
        return c

    def chompDelimiter(self):
        c=self.chompChar()
        self.issue(c)
        if c in "[(":
            self.parendepth+=1
        elif c in "])":
            self.parendepth-=1

            
    def chompWhitespace(self,withinToken=False):
        self.lexassert(len(self.source) > 0)
        c = self.source[0]
        self.source = self.source[1:]
        if c == '\t':
            self.column += 4-((self.column-1)%4)
        elif c == '\n':
            self.line += 1
            self.column = 1
            if self.parendepth==0 and self.cannewline and self.source:
                self.issue("\n")
                self.cannewline=False
        else:
            self.column += 1
        if not withinToken:
            self.markIssue()
        
    def chompOperator(self):
        token = ''
        while self.nxt() in OPERATORS:
            token += self.chompChar()
        self.issue(token)

    #
    # TOKENIZER
    #
    # This method defines the main loop of the
    # lexical analysis algorithm, one that converts
    # the source text into a list of token strings.

    def analyze(self):
        while self.source != '':
            # CHOMP a comment
            if self.source[0:2] == '(*':
                self.chompComment()
            # CHOMP whitespace
            elif self.source[0] in WHITESPACE:
                self.chompWhitespace()
            # CHOMP a single "delimiter" character
            elif self.source[0] in DELIMITERS:
                self.cannewline=True
                self.chompDelimiter()
            # CHOMP an operator               
            elif self.source[0] in OPERATORS:
                self.cannewline=True
                self.chompOperator()
            # CHOMP a reserved word or a name.
            else:
                self.cannewline=True
                self.chompWord()

