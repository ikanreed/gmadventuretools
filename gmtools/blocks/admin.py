from django.contrib import admin

# Register your models here.
from .models import BlockGroup, MonsterType, MonsterBaseBlock, Trait, StatsBlock, AlignmentBlock

admin.site.register([BlockGroup,MonsterType,MonsterBaseBlock,Trait,StatsBlock, AlignmentBlock])
