import re
def extract_wheezy(fileobj, keywords, comment_tags, options):
    """Extract messages from Wheezy files.

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    funcs = "|".join(keywords)
    regex = re.compile(r"@{\s*(?P<function>" + funcs + r")\('(?P<text>.+?)',?.*?\)")
    data = fileobj.read().decode()
    lineno = 0
    for line in data.split('\n'):
        lineno += 1
        ma = regex.findall(line)
        if len(ma) > 0:
            for m in ma:
                yield (lineno, m[0], m[1], [])