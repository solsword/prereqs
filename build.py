#!/usr/bin/env python

import jinja2
import sys, os

if len(sys.argv) != 8 or '-h' in sys.argv:
    print(
        "Usage: build.py <template> <css> <info> <extra_info> <js>"
      + " <content> <ouptut>"
    )
    exit(0)

(
    _,
    template_file,
    css_file,
    info_file,
    extra_info_file,
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

if os.path.exists(extra_info_file):
    with open(extra_info_file, 'r') as fin:
        extra_info = fin.read()
else:
    extra_info = {}

with open(content_file, 'r') as fin:
    content = fin.read()

result = template.render(
    css=css_code,
    info=info_code,
    extra_info=extra_info,
    js=js_code,
    content=content
)

with open(result_file, 'w') as fout:
    fout.write(result)
