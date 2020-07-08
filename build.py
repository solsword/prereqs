#!/usr/bin/env python

import jinja2
import sys

if len(sys.argv) != 7 or '-h' in sys.argv:
    print("Usage: build.py <template> <css> <json> <js> <content> <ouptut>")
    exit(0)

(
    _,
    template_file,
    css_file,
    info_file,
    js_file,
    content_file,
    result_file
) = sys.argv

with open(template_file, 'r') as fin:
    template = jinja2.Template(fin.read())

with open(css_file, 'r') as fin:
    css_code = fin.read()

with open(js_file, 'r') as fin:
    js_code = fin.read()

with open(info_file, 'r') as fin:
    info_code = fin.read()

with open(content_file, 'r') as fin:
    content = fin.read()

result = template.render(
    css=css_code,
    info=info_code,
    js=js_code,
    content=content
)

with open(result_file, 'w') as fout:
    fout.write(result)
