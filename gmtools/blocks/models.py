
from django.db import models
from model_utils.managers import InheritanceManager
#from gmtools.utils import dice
from utils import dice
from utils.mathutils import lerp

# Create your models here.



'''this is the root of all blocks,
whether they be stat blocks, ability blocks, feat blocks
description blocks, summary blocks, whatever
'''
class InformationBlock(models.Model):

    #name=models.CharField(max_length=256)
    priority=models.IntegerField()
    isSharable=models.BooleanField()
    objects=InheritanceManager()


    '''provide the given value, if we have it, None otherwise'''
    def provide(self, statname, provider, excludeList):
        return None
    '''return a set of stats that this needs to have fulfilled to be fully descibed'''
    def requires(self):
        return set()

class Trait(InformationBlock):
    name=models.CharField(max_length=80)
    description=models.CharField(max_length=1800)#a page of a book should cover any traits

    def __str__(self):
        return self.name

class MonsterType(InformationBlock):
    HitDiceType=models.CharField(max_length=10)
    name=models.CharField(max_length=80)
    attackProgression=models.CharField(
        max_length=6,
        choices=(
            ('SLOW','1/2 HD'),
            ('MEDIUM','3/4 HD'),
            ('FAST','=HD'))
        )
    goodWill=models.BooleanField(null=False)
    goodFort=models.BooleanField(null=False)
    goodRef=models.BooleanField(null=False)
    skill_base=models.IntegerField(null=False)
    CR20HD=models.IntegerField(null=False)
    defaultTraits=models.ManyToManyField(Trait, related_name='monster_types',blank=True)

    def provide(self, statname, provider, excludeList):
        return {
            "HitDiceType":self.HitDiceType,
            "type":self.name,
            "attackProgression":self.attackProgression,
            "goodRef":self.goodRef,
            "goodFort":self.goodFort,
            "goodWill":self.goodWill,
            "CR20HD":self.CR20HD,#we don't expect it to get overridden, but whatever
            "skill_base":self.skill_base,
        }.get(statname,None)
    #foreign key to default abilities type soon

    def __str__(self):
        return self.name

class StatsBlock(InformationBlock):
    strength=models.IntegerField()
    dexterity=models.IntegerField()
    constitution=models.IntegerField()
    intelligence=models.IntegerField()
    wisdom=models.IntegerField()
    charisma=models.IntegerField()
    def provide(self, statname, provider, excludeList):
        if hasattr(self, statname):
            return getattr(self, statname)
        return {
            'STR':self.getbonus(provider.strength),
            'DEX':self.getbonus(provider.dexterity),
            'CON':self.getbonus(provider.constitution),
            'INT':self.getbonus(provider.intelligence),
            'WIS':self.getbonus(provider.wisdom),
            'CHA':self.getbonus(provider.charisma)
        }.get(statname, None)
    def getbonus(self, value):
        if(value=='-'):
            return 0
        return (value-10)//2

    #no point overriding str with a bunch of nonsense about our stats

class MonsterBaseBlock(InformationBlock):
    #we don't know of any important features to set
    #we COULD even just have this table not exist
    HD=models.IntegerField()
    speed=models.IntegerField()
    CR=models.IntegerField(null=True)

    def calc_save(self, good, stat, CR):
        if good:
            return round(lerp(2,20,CR/20))+stat
        else:
            return round(lerp(0,15,CR/20))+stat

    def provide(self, statname, provider, excludeList):
        if statname=="HP":
            hdDice=dice.BulkDieRoll(provider.provide_value("HD"))
            conBonus=provider.CON
            return min(hdDice.avg()[0] + hdDice.countDice()*conBonus, hdDice.countDice())
        if statname=="HD":
            dicetype=provider.HitDiceType
            return str(self.HD)+dicetype
        if statname=="speed":
            return self.speed
        if statname=="skillpoints":
            hd=dice.BulkDieRoll(provider.provide_value("HD")).countDice()
            baseval=provider.skill_base
            intbonus=provider.INT
            perdie=min(baseval+intbonus,1)
            return hd*perdie
        if statname=="will":
            good=provider.goodWill
            wis=provider.WIS
            return self.calc_save(good, wis, provider.CR)
        if statname=="fort":
            good=provider.goodFort
            con=provider.CON
            return self.calc_save(good, con, provider.CR)
        if statname=="ref":
            good=provider.goodRef
            dex=provider.DEX
            return self.calc_save(good, dex, provider.CR)
        if statname=="BAB":
            progression=provider.provide_value('attackProgression')
            hd=dice.BulkDieRoll(provider.HD).countDice()
            {'SLOW':hd//2,
            'MEDIUM':hd*3//4,
            'FAST':hd}.get(progression, None)
        if statname=="CR":#we provide an estimate, later add a fixed cr
            if self.CR:
                return self.CR
            hdDice=dice.BulkDieRoll(provider.HD).countDice()
            cr20hd=provider.provide_value("CR20HD") or 20
            diff=cr20hd-20
            a=(diff-1)/400
            return round(((4*a*(hdDice-1)+1)**0.5-1)/(2*a))



    #just inherit default requires

class ProviderWrapper:
    def __init__(self, wrapped):
        self.wrapped=wrapped
    def provide_value(self, name, rootprovider=None, excludeList=set()):
        return self.wrapped.provide_value(name, rootprovider,excludeList)
    def __getattr__(self, name):
        return self.provide_value(name)

class BlockGroup(models.Model):
    #does this actually store anything about the group of blocks?
    #at all?
    blocks=models.ManyToManyField(InformationBlock, related_name="groups", blank=True)
    #okay we want to know if there's something we're extending
    base_group=models.ForeignKey('BlockGroup', related_name="inheritors", null=True, on_delete= models.CASCADE)
    def all_blocks(self):
        result= [x for x in self.blocks.select_subclasses()]
        if(self.base_group is not None):
            result=self.base_group.all_blocks()+result
        return result
    def unprovidedValues(self):
        missing=set()
        for block in self.blocks.select_subclasses():
            for req in block.requires():
                if self.provide_value(req) is None:
                    missing.add(req)
        if self.base_group is not None:
            missing=missing.union(self.base_group.unprovidedValues())
        return sorted(missing)

    def provide_value(self, statname, rootprovider=None, excludeList=set()):
        rootprovider = rootprovider or ProviderWrapper(self)
        for block in self.blocks.order_by('priority').select_subclasses():
            if block not in excludeList:
                provided=block.provide(statname, rootprovider, excludeList)
                if provided is not None:
                    return provided
        if(self.base_group is not None):
            return self.base_group.provide_value(statname, rootprovider, excludeList)
        #explicit, but this intended if nothing found
        return None
