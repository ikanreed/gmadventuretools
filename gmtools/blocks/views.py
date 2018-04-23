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
    missingvalues=[]
    group.reportMissing=missingvalues.append
    context={'group':group,
        'blocks': [x.render(group,request,False) for x in sorted(group.blocks.select_subclasses(),
            key=lambda x:x.displayorder)],
        'missingvalues':missingvalues}
    return render(request, 'showblockgroup.html', context)
