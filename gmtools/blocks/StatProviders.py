class ProviderDictionary(dict):
    def __init__(self, wrapped, force_exclude=None):
        if isinstance(wrapped,  ProviderWrapper):
            self.wrapped=wrapped
        else:
            self.wrapped=ProviderWrapper(wrapped)
        self.exclude=force_exclude
    def __getitem__(self, key):
        return self.provide_value(key)
    def __contains__(self, key):
        return self.provide_value(key) is not None
    def provide_value(self, name, rootprovider=None, excludeList=set()):
        if self.exclude:
            excludeList=excludeList.union(force_exclude)
        return self.wrapped.provide_value(name, rootprovider or self.wrapped,excludeList)

class ProviderWrapper:
    def __init__(self, wrapped):
        self.wrapped=wrapped
        self.cache={}
    def provide_value(self, name, rootprovider=None, excludeList=set()):
        #we could infinite lookup prevent too...
        if name in self.cache and not excludeList:
            return self.cache[name]
        result= self.wrapped.provide_value(name, rootprovider or self,excludeList)
        self.cache[name]=result
        return result
    def __getattr__(self, name):
        if name=='wrapped' or name=="cache":
            return super().__getattr__(name)
        return self.provide_value(name,self)
    def BlocksOfType(self, blocktype):
        return self.wrapped.BlocksOfType(blocktype)

class IntProvider:
    def __init__(self, wrapped):
        self.wrapped=wrapped
    def __getattr__(self, name):
        if name=='wrapped':
            return super().__getattr__(name)
        return int(getattr(self.wrappped, name) or 0)
