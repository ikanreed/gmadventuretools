from django.db import models
from blocks import models as blockmodels
# Create your models here.


class SharedBlock(models.Model):
    block=models.ForeignKey(blockmodels.InformationBlock, related_name="shared_as", on_delete=models.CASCADE)
    name=models.CharField(max_length=80)
    @staticmethod
    def get_shared_query(BlockType, **kwQueryArgs):
        if kwQueryArgs:
            possibleTargets=BlockType.objects.filter(**kwQueryArgs)
        else:
            possibleTargets=BlockType.objects.all()
        possibleTargets=possibleTargets.filter(shared_as__in=SharedBlock.objects.all())
        return possibleTargets

class BlockType(models.Model):
    name=models.CharField(max_length=80)
    blocktypename=models.CharField(max_length=120)
    manualblocks=models.ManyToManyField(blockmodels.InformationBlock)


class PointAllocatorType(models.Model):
    name=models.CharField(max_length=80)
    unspentpointfieldname=models.CharField(max_length=80)
    blocktype=models.ForeignKey(BlockType, on_delete=models.CASCADE )

class PointAllocator(models.Model):
    name=models.CharField(max_length=80)
    allocationType=models.ForeignKey(PointAllocatorType, on_delete=models.CASCADE)
    filteritem=models.CharField(max_length=200)
    getsortvalforitem=models.CharField(max_length=200)

class Wizard(models.Model):
    name=models.CharField(max_length=80)
    pointallocators=models.ManyToManyField(PointAllocatorType, blank=True)
    def get_possible_blocktypes(self):
        return blockmodels.InformationBlock.__subclasses__()




class WizardBlock(models.Model):
    wizard=models.ForeignKey(Wizard, null=False, on_delete=models.CASCADE, related_name="Blocks")
    blocktype=models.CharField(max_length=100, null=False)
    allowmultiple=models.BooleanField()
    required=models.BooleanField()
    orderIndex=models.IntegerField()
    alwayscustom=False
    def GetOptions(self):

        return SharedBlock.objects.filter()
    class Meta:
        unique_together=(('wizard', 'orderIndex'),)
