from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def listblocks(request):
    vard=dict(vars(request))

    requestvars="<br />".join([str(x)+"::"+str(vard[x]) for x in vard])
    return HttpResponse("<br />the content of the request is <br />"+requestvars)
