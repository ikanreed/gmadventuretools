from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from . import models
# Create your views here.

def listblocks(request):
    allGroups=models.BlockGroup.objects.all()
    context={'blockgroups':allGroups}
    return render(request, 'listblocks.html',context)

def showblock(request, group_id):
    group=get_object_or_404(models.BlockGroup, pk=group_id)
    context={'group':group, 'blocks': [x.render(group,request,False) for x in group.blocks.select_subclasses()]}
    return render(request, 'editblockgroup.html', context)
