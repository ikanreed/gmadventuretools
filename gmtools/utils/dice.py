import re
import random
from utils.tokenizer import *

class DieRoll:
    def __init__(self, count, sides):
        if count:
            self.count=int(count)
        else:
            self.count=1
        self.sides=int(sides)
    def avg(self):
        return ((self.sides+1)*self.count//2), (self.sides+1)*self.count%2
    def max(self):
        return self.count*self.sides
    def min(self):
        return self.count
    def roll(self):
        return sum(random.randint(1,self.sides) for x in range(self.count))
    def countDice(self):
        return self.count

class Constant:
    def __init__(self, value):
        self.value=int(value)
    def avg(self):
        return self.value,0
    def max(self):
        return self.value
    def min(self):
        return self.value
    def roll(self):
        return self.value
    def countDice(self):
        return 0
class Sum:
    def __init__(self,left, right):
        self.left=left
        self.right=right
    def avg(self):
        leftval,leftremainder=self.left.avg()
        rightval, rightremainder=self.right.avg()
        return leftval+rightval+(leftremainder+rightremainder)//2,(leftremainder+rightremainder)%2
    def max(self):
        return self.left.max()+self.right.max()
    def min(self):
        return self.left.min()+self.right.min()
    def roll(self):
        return self.left.roll()+self.right.roll()
    def countDice(self):

        return self.left.countDice()+self.right.countDice()
class Difference:
    def __init__(self,left, right):
        self.left=left
        self.right=right
    def avg(self):
        leftval,leftremainder=self.left.avg()
        rightval, rightremainder=self.right.avg()
        return leftval-rightval+(leftremainder-rightremainder)//2,(leftremainder-rightremainder)%2
    def max(self):
        return self.left.max()-self.right.max()
    def min(self):
        return self.left.min()-self.right.min()
    def roll(self):
        return self.left.roll()-self.right.roll()
    def countDice(self):
        #reallllllllllllllly uncertain here
        #do we add or subtract, i guess add?
        return self.left.countDice()+self.right.countDice()

class MultiRoll:
    def __init__(self, left, right):
        self.left=left
        self.right=right
    def avg(self):
        leftval, lremainder=self.left.avg()
        rightval, rremainder=self.right.avg()
        #we'll cut the remainder from this because quarters are not a thing we like
        return (leftval*rightval+(leftval*rremainder + rightval*lremainder)//2,0)
    def max(self):
        return self.left.max()*self.right.max()
    def min(self):
        #does not handle zeros well
        return self.left.min()*self.right.min()
    def roll(self):
        return sum(self.right.roll() for x in range(self.left.roll()))
    def countDice(self):
        if self.left.countDice() and self.right.countDice():
            #if someone uses this somehow, we'll sort it out then
            return self.left.countDice() + self.right.countDice()
        elif self.left.countDice():
            return self.left.countDice()*self.right.avg()
        elif self.right.countDice():
            return self.right.countDice()*self.left.avg()
        else:
            return 0
class BulkDieRoll:
    dietokenizer=Tokenizer(
        atom('(?P<count>[0-9]*)d(?P<sides>[0-9]+)',DieRoll),
        atom('(?P<value>[0-9]+)',Constant),
        binop('+', Sum),
        binop('-', Difference),
        binop('*',MultiRoll),
        grouping('(',')')
    )
    def __init__(self, diestring):
        if hasattr(diestring,'roll'):
            self.root=diestring#not a string, already made
        else:
            self.root=self.dietokenizer.tokenize(diestring)


    def avg(self):
        return self.root.avg()
    def max(self):
        return self.root.max()
    def min(self):
        return self.root.min()
    def roll(self):
        return self.root.roll()
    def countDice(self):
        return self.root.countDice()
    def getMultipleRoll(self, times):
        return BulkDieRoll(MultiRoll(times,self.root))
