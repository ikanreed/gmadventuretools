import re

class Tokenizer:
    def __init__(self, *tokenTypes):
        self.tokenTypes=tokenTypes
        for token in self.tokenTypes:
            token.tokenizer=self

    def tokenize(self, tokenString):
        for token in self.tokenTypes:
            if token.CanMatch(tokenString):
                return token.BuildToken(tokenString)
            elif token.CanMatch(tokenString.strip()):#purely convenience
                return token.BuildToken(tokenstring.strip())



class TokenType:
    def __init__(self):
        self.tokenizer=None
    def CanMatch(self, string):
        return False

class AtomTokenType(TokenType):
    def __init__(self, regularExpression, kwcallable):
        self.invocation=kwcallable
        if(isinstance(regularExpression, str)):
            self.regex=re.compile(regularExpression)
        else:
            self.regex=regularExpression
    def CanMatch(self, string):
        return self.regex.fullmatch(string)
    def BuildToken(self, string):
        match=self.regex.fullmatch(string)
        return self.invocation(**match.groupdict())

atom=AtomTokenType

class BinaryOperatorTokenType(TokenType):
    def __init__(self, operatorstring, twoargcallable):
        self.invocation=twoargcallable
        self.operatorstring=operatorstring
    def CanMatch(self, string):
        if(self.operatorstring in string):
            left, op, right=string.partition(self.operatorstring)
            return self.tokenizer.tokenize(left) and self.tokenizer.tokenize(right)
    def BuildToken(self, string):
        left, op, right=string.partition(self.operatorstring)
        return self.invocation(self.tokenizer.tokenize(left), self.tokenizer.tokenize(right))
binop=BinaryOperatorTokenType


class UnaryOperatorTokenType(TokenType):
    def __init__(self, operatorstring, oneargcallable):
        self.invocation=oneargcallable
        self.operatorstring=operatorstring
    def CanMatch(self, string):
        if string.startswith(self.operatorstring):
            left, op, right=string.partition(self.operatorstring)
            return self.tokenizer.tokenize(right)
    def BuildToken(self, string):
        left, op, right=string.partition(self.operatorstring)
        return self.invocation(self.tokenizer.tokenize(right))

unop=UnaryOperatorTokenType


class GroupingTokenType(TokenType):
    #we could do things like comma delimitation right here, but naaah
    def __init__(self,startstring, endstring):
        self.start, self.end=startstring,endstring
    def CanMatch(self, string):
        if(string.startswith(startstring) and string.endswith(endstring)):
            return self.tokenizer.tokenize(string[len(startstring):-len(endstring)])
    def BuildToken(self, string):
        return self.tokenizer.tokenize(string[len(startstring):-len(endstring)])

grouping=GroupingTokenType
