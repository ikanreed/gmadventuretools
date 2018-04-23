from django.contrib import admin

# Register your models here.
from .models import BlockGroup, MonsterType, MonsterBaseBlock, Trait, StatsBlock, AlignmentBlock
from .models import DefensesBlock, OffenseBlock, SizeBlock, Weapon, Attack

admin.site.register([BlockGroup,MonsterType,MonsterBaseBlock,Trait,StatsBlock, \
    AlignmentBlock, DefensesBlock, OffenseBlock,SizeBlock, Weapon, Attack])
