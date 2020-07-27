#!/usr/bin/env python

import jinja2
import json
import sys

if len(sys.argv) != 6 or '-h' in sys.argv:
    print(len(sys.argv))
    print("Usage: build-alt.py <template> <css> <json> <js> <output>")
    exit(0)

(
    _,
    template_file,
    css_file,
    info_file,
    js_file,
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
    info_dict = json.loads(info_code)
    info_list = sorted( tuple(info_dict.items()) )

result = template.render(
    css=css_code,
    courses=info_list,
    js=js_code
)

with open(result_file, 'w') as fout:
    fout.write(result)
