
from django.db import models
import sys
from model_utils.managers import InheritanceManager
from django.template import loader
from django.conf import settings
import math
#from gmtools.utils import dice
from utils import dice
from utils.mathutils import lerp
from .StatProviders import ProviderDictionary, ProviderWrapper, IntProvider

# Create your models here.




'''this is the root of all blocks,
whether they be stat blocks, ability blocks, feat blocks
description blocks, summary blocks, whatever
'''
class InformationBlock(models.Model):
    owner=models.ForeignKey(settings.AUTH_USER_MODEL, default=None, null=True, on_delete=models.SET_NULL)
    created=models.DateTimeField(auto_now_add=True)
    modified=models.DateTimeField(auto_now=True)
    #name=models.CharField(max_length=256)
    priority=10
    displayorder=0
    objects=InheritanceManager()


    '''provide the given value, if we have it, None otherwise'''
    def provide(self, statname, provider, excludeList):
        #a more sensible default is to provide the stat if we have it as a variable
        if hasattr(self, statname):
            return getattr(self, statname)
        #return None
    def modify(self, statname, unmodded, provider, excludeList):
        return None
    '''return a set of stats that this needs to have fulfilled to be fully descibed'''
    def requires(self):
        return set()
    def assign(self,group):
        pass
    def unassign(self,group):
        pass

    def render(self, block, request,isedit):
        wrap=ProviderDictionary(block)
        template=self.template(isedit)
        if template:
            if hasattr(template, 'render'):
                return template.render(wrap, None)
            elif template is str:
                return template
        else:
            return ""
    def template(self,isedit):
        return None

    def __str__(self):
        if(type(self)==InformationBlock):
            return str(InformationBlock.objects.select_subclasses().get(pk=self.pk))
        else:
            return super().__str__()



class Feat(InformationBlock):
    name=models.CharField(max_length=80)
    description=models.CharField(max_length=1800)
    prerequisite_feats=models.ManyToManyField("Feat", related_name="prerequisite_for")
    prerequisiteExpression=models.CharField(max_length=200)
    def prerequisites_met(self,provider):
        newExclude={self}
        localproxy=ProviderDictionary(provider,newExclude)
        #kicking security mistakes into high gear
        return eval(expr, {}, localproxy)

class Weapon(InformationBlock):#it's an information block, but not for a monster
    name=models.CharField(max_length=80)
    usage=models.CharField(max_length=20, choices=(('melee', 'melee'),('ranged','ranged')))
    isnatural=models.BooleanField()
    damagetype=models.CharField(max_length=20)
    mediumdamage=models.CharField(max_length=5)#"10d12" is a kind of unreasonable high end
    critical=models.CharField(max_length=20, blank=True)
    size=models.CharField(max_length=20)

    def template(self, isedit):
        if isedit:
            return loader.get_template(template_name="editblock/weapon.html")
        else:
            return loader.get_template(template_name="showblock/weapon.html")
    def __str__(self):
        return "%s (%s)"%(self.name, self.mediumdamage)
class AttackBlurb:
    def __init__(self, bonus, count, name, damageroll, addedeffect,critical, weapon):
        self.bonus=bonus
        self.count=count
        self.name=name
        self.damageroll=damageroll
        self.addedeffect=addedeffect
        self.critical=critical
        self.weaponobject=weapon

class Attack(InformationBlock):
    priority=4
    usedweapon=models.ForeignKey(Weapon, on_delete=models.PROTECT)
    count=models.IntegerField(default=1)
    addedEffect=models.CharField(max_length=30, blank=True, default='')


    def __str__(self):
        return "%sx %s"%((self.count or 1),self.usedweapon.name)

    def provide(self, statname, provider, excludeList):
        if statname=="attacks":
            statbonus=0
            damagebonus=0
            if self.usedweapon.usage in ('melee', 'touch'):
                statbonus=provider.STR
                damagebonus=provider.STR
                if self.usedweapon.size=="offhand":
                    damagebonus=provider.STR//2
                if self.usedweapon.size=="twohand":
                    damagebonus=provider.STR*3//2
            if self.usedweapon.usage in ("ranged", 'ranged touch'):
                statbonus=provider.DEX
                if self.usedweapon.usage=="thrown":
                    damagebonus=provider.STR
            totalbonus=statbonus+provider.BAB
            damageroll=self.usedweapon.mediumdamage
            if damagebonus>0:
                damageroll="%s+%s"%(damageroll, damagebonus)
            elif damagebonus<0:
                damageroll="%s-%s"%(damageroll,-damagebonus)
            attack=AttackBlurb(totalbonus, self.count, self.usedweapon.name, damageroll,\
                self.addedEffect, self.usedweapon.critical, self.usedweapon)
            return GroupedItem(attack, (self.usedweapon.usage, self.usedweapon.isnatural))


class SizeBlock(InformationBlock):
    priority=8#size is pretty important and changes everything
    sizecodes={
        -4:'Fine',
        -3:'Diminutive',
        -2:'Tiny',
        -1:'Small',
        0:'Medium',
        1:'Large',
        2:'Huge',
        3:'Gargantuan',
        4:'Colossal'}
    size=models.IntegerField(choices=tuple(sorted(sizecodes.items())))
    def provide(self, statname, provider, excludeList):
        ex=excludeList.union({self})#we're gonna do a LOT of recursing
        if statname=="size":
            return self.sizecodes[provider.sizesteps]
        if statname=="sizesteps":
            return self.size
        if statname=="space" or statname=="reach":
            size=provider.sizesteps
            if size>0:
                return 5*size
            elif size==0:
                return 5
        if statname=="sizemod":
            size=provider.sizesteps
            if(size==0):
                return 0
            return -self.getsign(size)*2**(abs(size)-1)
    def modify(self, statname,baseval, provider, excludeList):
        if statname=="strength":
            mod={-4:-10,-3:-10,-2:-8,-1:-4,0:0,1:8,2:16,3:24,4:32}.get(provider.sizesteps,0)
            return max(1,baseval+mod)
        if statname=="dexterity":
            mod={-4:8,-3:6,-2:4,-1:2,0:0,1:-2,2:-4,3:-4,4:-4}.get(provider.sizesteps,0)
            return max(1,baseval+mod)
        if statname=="constitution":
            mod={-4:-2,-3:-2,-2:-2,-1:-2,0:0,1:4,2:8,3:12,4:16}.get(provider.sizesteps,0)
            return max(1, baseval+mod)
        if statname=="NaturalArmor":
            mod={1:2,2:5,3:9,4:13}.get(provider.sizesteps,0)
            return baseval+mod
        if statname=="AC" or statname=="Fly" or statname=="touch" or statname=="flatfooted":
            print('base %s, sizemod %s'%(baseval,provider.sizemod))
            return baseval+provider.sizemod
        if statname=="attacks":
            return {x:[self.scaleAttack(z, provider) for z in y] for x,y in baseval.items()}
        if statname=="CMB" or statname=="CMD":
            result=baseval-provider.sizemod
            return result
        if statname=="Stealth":
            return baseval+provider.sizemod*2
    def scaleAttack(self, attack, provider):
        newroll=dice.BulkDieRoll(attack.damageroll)
        for diegroup in newroll.getDieRollObjects():
            for i in range(provider.sizesteps):
                self.growdice(diegroup)
            for i in range(-provider.sizesteps):
                self.shrinkdice(diegroup)
        print(attack.name)
        return AttackBlurb(attack.bonus+provider.sizemod,attack.count, attack.name, newroll.toDiceString(),
            attack.addedeffect, attack.critical, attack.weaponobject)
    def shrinkdice(self, dieroll):
        if dieroll.count>1:
            dieroll.count=dieroll.count//2
            dieroll.sides=dieroll.sides+2
        else:
            dieroll.sides={1:0,2:1,3:2,4:3,6:4,8:6,10:8,12:10,20:12}.get(dieroll.sides,dieroll.sides-1)
    def growdice(self, dieroll):
        if dieroll.sides==1:
            dieroll.sides=2
        elif dieroll.sides==2:
            dieroll.sides=3
        elif dieroll.sides==3:
            dieroll.sides=4
        elif dieroll.sides==4:
            dieroll.sides=6
        elif dieroll.sides==6:
            dieroll.sides=8
        elif dieroll.sides==8:
            dieroll.sides=6
            dieroll.count=dieroll.count*2
        elif dieroll.sides==10:
            dieroll.sides=8
            dieroll.count=dieroll.count*2
        elif dieroll.sides==12:
            dieroll.sides=6
            dieroll.count=dieroll.count*3
        else:
            print('unable to scale damage %s'%dieroll.toDiceString())

    def getsign(self,value):
        if(value<0):
            return -1
        return 1

    def __str__(self):
        return "Size: "+self.sizecodes[self.size]

class SingleItem:
    def __init__(self, item):
        self.item=item

class GroupedItem:
    def __init__(self, item, key):
        self.item=item
        self.key=key

class Trait(InformationBlock):
    priority=5
    name=models.CharField(max_length=80)
    description=models.CharField(max_length=1800)#a page of a book should cover any traits
    isDefensive=models.BooleanField(default=False)
    isOffesnive=models.BooleanField(default=False)
    update_expr=models.CharField(max_length=200, blank=True,null=True)

    def __str__(self):
        return self.name

    def provide(self, statname, provider, excludeList):
        if self.update_expr:
            changedstat, equals, expr=update_expr.partition('=')
            if statname==changedstat.strip():
                newExclude=excludeList.union({self})
                localproxy=ProviderDictionary(provider,newExclude)
                #kicking security mistakes into high gear
                return eval(expr, {}, localproxy)
        if statname=="DefensiveTraits" and self.isDefensive:
            return SingleItem(self)
        if statname=="OffensiveTraits" and self.isOffesnive:
            return SingleItem(self)

class SpecialAttack(InformationBlock):
    priority=5
    name=models.CharField(max_length=80)
    description=models.CharField(max_length=1800)
    def __str__(self):
        return self.name
    def provide(self):
        if name=="specialattacks":
            return SingleItem(self)

class Skill(models.Model):
    name=models.CharField(max_length=30)
    stat=models.CharField(max_length=3)
    armorCheck=models.BooleanField()

class MonsterType(InformationBlock):
    priority=2
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
    classSkills=models.ManyToManyField(Skill, related_name='monster_types', blank=True)

    def assign(self, group):
        for trait in self.defaultTraits:
            if not group.blocks.filter(pk=trait.pk).exists():
                group.assign_block(trait)
    def unassign(self, group):
        for trait in self.defaultTraits:
            if group.blocks.filter(pk=trait.pk).exists():
                group.unassign_block(trait)

    def provide(self, statname, provider, excludeList):
        if statname.endswith('isclassskill'):
            skillname=statname.replace('isclassskill','')
            if classSkills.filter(name=skillname).exists():
                return True
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
class DefensesBlock(InformationBlock):
    displayorder=2
    priority=3
    naturalArmor=models.IntegerField(null=True,blank=True)
    def template(self, isedit):
        if isedit:
            return loader.get_template('editblock/DefensesBlock.html')
        else:
            return loader.get_template('showblock/DefensesBlock.html')
    def calc_save(self, good, stat, CR):
        if good:
            return round(lerp(2,20,CR/20))+stat
        else:
            return round(lerp(0,15,CR/20))+stat
    def provide(self,statname, provider, excludeList):
        if statname=="NaturalArmor":
            if self.naturalArmor:
                return self.naturalArmor
            else:
                #approximate natural armor as CR for fast monsters
                #size will add more
                return provider.CR
        if statname=="AC":
            return 10 +\
                (provider.NaturalArmor or 0) +\
                (provider.DEX or 0)
        if statname=="touch":
            return 10 + (provider.DEX or 0)
        if statname=="flatfooted":
            dex=0
            if (provider.DEX or 0)<0:
                dex=provider.DEX
            return 10 + (provider.NaturalArmor or 0)+dex
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

class OffenseBlock(InformationBlock):
    displayorder=3
    priority=2
    def template(self, isedit):
        if isedit:
            return loader.get_template('editblock/OffensesBlock.html')
        else:
            return loader.get_template('showblock/OffensesBlock.html')
    def provide(self,statname, provider, excludeList):
        if statname=="BAB":
            progression=provider.attackProgression
            hd=provider.HD
            return {'SLOW':hd//2,
            'MEDIUM':hd*3//4,
            'FAST':hd}.get(progression, None)
        if statname=="CMB":
            result=(provider.BAB or 0)+(provider.STR or 0)
            return result
        if statname=="CMD":
            return 10+(provider.BAB or 0)+(provider.STR or 0)+(provider.DEX or 0)

class StatsBlock(InformationBlock):
    displayorder=4
    priority=2
    strength=models.IntegerField()
    dexterity=models.IntegerField()
    constitution=models.IntegerField()
    intelligence=models.IntegerField()
    wisdom=models.IntegerField()
    charisma=models.IntegerField()

    def template(self, isedit):
        if isedit:
            return loader.get_template('editblock/StatBlock.html')
        else:
            return loader.get_template('showblock/StatBlock.html')

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
class AlignmentBlock(InformationBlock):
    priority=3
    lawchaos=models.CharField(max_length=1, choices=(('L','Lawful'),('N','Neutral'),('C','Chaotic')))
    goodevil=models.CharField(max_length=1, choices=(('G','Good'),('N','Neutral'),('E','Evil')))
    def provide(self, statname, provider, excludeList):
        if statname=="alignment":
            if self.lawchaos==self.goodevil:
                return "N"
            return self.lawchaos+self.goodevil


class SkillRank(InformationBlock):
    skill=models.ForeignKey(Skill, on_delete=models.CASCADE)
    ranks=models.IntegerField()
    priority=3
    def provide(self, statname, provider, excludeList):
        if statname==skill.name:
            statvalue=provider.provide_value(skill.stat.upper()) or 0
            if provider.provide_value(statname+"isclassskill"):
                return statvalue+ranks+3
            return statvalue+ranks
        if statname=="skillswithranks" and self.ranks!=0:
            return SingleItem((self,provider.provide(skill.name)))


class MonsterBaseBlock(InformationBlock):
    #we don't know of any important features to set
    #we COULD even just have this table not exist
    priority=2
    displayorder=1
    HD=models.IntegerField()
    speed=models.IntegerField()
    CR=models.IntegerField(null=True)
    name=models.CharField(max_length=80)

    def provide(self, statname, provider, excludeList):
        if statname=="HP":
            hdDice=dice.BulkDieRoll(provider.HDText)
            #conBonus=provider.CON
            return max(hdDice.avg()[0], hdDice.countDice())
        if statname=="HDText":
            dicetype=provider.HitDiceType

            return str(self.HD)+dicetype+"+"+str(self.HD*provider.CON)
        if statname=="HD":
            return dice.BulkDieRoll(provider.HDText).countDice()
        if statname=="speed":
            return self.speed
        if statname=="skillpoints":
            hd=provider.HD
            baseval=provider.skill_base
            intbonus=provider.INT
            perdie=min(baseval+intbonus,1)
            return hd*perdie
        if statname=="featcount":
            return (provider.HD+1)//2
        if statname=="unspentskills":
            points=provider.skillpoints
            spent
        if statname=="CR":#we provide an estimate, later add a fixed cr
            if self.CR:
                return self.CR
            hdDice=provider.HD
            cr20hd=provider.CR20HD or 20
            diff=cr20hd-20
            a=(diff-1)/400
            return round(((4*a*(hdDice-1)+1)**0.5-1)/(2*a))
        if statname=="XP":
            if(provider.CR is not None):
                if(provider.CR>0):
                    sum=400
                    for i in range(1,provider.CR):
                        added=2**((i+1)//2)*100
                        sum+=added
                    return sum
                elif CR==0:
                    return 200
                else:#technically lower is possible
                    return 100
        if statname=="CRText":
            cr=provider.CR
            if cr>0:
                return str(cr)
            elif cr==0:
                return "1/2"
            elif cr==-1:
                return "1/4"
            elif cr<-1:
                return "1/8"#it doesn't get any easier than that
        if statname=="initiative":
            return provider.DEX
        if statname=="name":
            return self.name
    def template(self, isedit):
        if isedit:
            return loader.get_template('editblock/MonsterSummary.html')
        else:
            return loader.get_template('showblock/MonsterSummary.html')




debugstatnames=["attacks"]

class BlockGroup(models.Model):
    #does this actually store anything about the group of blocks?
    #at all?
    blocks=models.ManyToManyField(InformationBlock, related_name="groups", blank=True)
    #okay we want to know if there's something we're extending
    base_group=models.ForeignKey('BlockGroup', related_name="inheritors", null=True, blank=True, on_delete= models.CASCADE)

    def assign_block(self, block):
        #this should be the only place blocks.add is called
        self.blocks.add(block)
        block.assign(self)
    def unassign_block(self, block):
        self.blocks.remove(block)
        block.unassign(self)

    def all_blocks(self):
        result= [x for x in self.blocks.select_subclasses()]
        if(self.base_group is not None):
            result=self.base_group.all_blocks()+result
        return result
    def BlocksOfType(self, blocktype):
        return [x for x in self.all_blocks() if x is blocktype]

    def provide_value(self, statname, rootprovider=None, excludeList=set()):
        if statname in debugstatnames:
            print('providing %s'%statname)
        try:
            result=self._provide_inner(statname, rootprovider, excludeList)
        except Exception as e:
            import traceback
            print(e, file=sys.stderr)
            traceback.print_tb(e.__traceback__, file=sys.stderr)
            if(hasattr(self, 'reportMissing')):
                self.reportMissing(statname)
            return None
        if result is None:
            if(hasattr(self, 'reportMissing')):
                self.reportMissing(statname)
            return None
        try:
            result=self._modify_inner(statname,result,rootprovider,excludeList)
        except Exception as e:
            import traceback
            print(e, file=sys.stderr)
            traceback.print_tb(e.__traceback__, file=sys.stderr)
            if(hasattr(self, 'reportMissing')):
                self.reportMissing(statname)
            #return the unmodified value?
            return None

        if statname in debugstatnames:
            print('provided %s as %s'%(statname,result))
        return result

    def _modify_inner(self, statname, result, rootprovider,excludeList):
        for block in sorted(self.blocks.select_subclasses(), key=lambda x: x.priority, reverse=False):
            if block not in excludeList:
                if statname in debugstatnames:
                    print('before call %s'%block)
                newval=block.modify(statname, result, rootprovider,excludeList)
                if statname in debugstatnames:
                    print('attempting to modify %s with %s, modified value: %s'%(statname, block,newval))
                if newval is not None:
                    result=newval
        return result

    def _provide_inner(self, statname, rootprovider,excludeList):
        rootprovider = rootprovider or ProviderWrapper(self)
        #priority is not a database field, it really just reflects the
        #importance of the KIND of block
        if statname in debugstatnames:
            print('starting lookup for stat %s with excludeList %s'%(statname, excludeList))
        for block in sorted(self.blocks.select_subclasses(), key=lambda x: x.priority, reverse=True):
            if block not in excludeList:

                provided=block.provide(statname, rootprovider, excludeList)
                if provided is not None:
                    if isinstance(provided,SingleItem):
                        #go through whole stack and build list
                        return [provided.item]+(self._provide_inner(statname,rootprovider,excludeList.union({block})) or [])
                    if isinstance(provided, GroupedItem):
                        others=dict(self._provide_inner(statname,rootprovider,excludeList.union({block})) or {})
                        val=others.get(provided.key,[])+[provided.item]
                        result=dict(others)
                        result[provided.key]=val
                        return result
                    return provided
        if(self.base_group is not None):
            return self.base_group.provide_value(statname, rootprovider, excludeList)
        #explicit, but this intended if nothing found

        return None
    def summary(self):
        wrap=ProviderWrapper(self)
        return wrap.name or wrap.description or wrap.type+"("+str(wrap.CR)+")"
