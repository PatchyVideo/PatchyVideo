
def makeUTF8(x):
    if isinstance(x, str):
        return x.encode('utf-8')
    if isinstance(x, dict):
        new_dict = {}
        for k in x:
            if isinstance(k, str):
                new_dict[k.encode('utf-8')] = makeUTF8(x[k])
            else:
                new_dict[k] = makeUTF8(x[k])
        return new_dict
    return x
