#!/usr/bin/env python

import jinja2
import json
import sys, os

if len(sys.argv) != 7 or '-h' in sys.argv:
    print("Got", len(sys.argv), "arguments...")
    print(
        "Usage: build_alt.py <template> <css> <info> <extra_info> <js>"
        " <output>"
    )
    exit(0)

(
    _,
    template_file,
    css_file,
    info_file,
    extra_info_file,
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
    info_dict = json.load(fin)

if os.path.exists(extra_info_file):
    with open(extra_info_file, 'r') as fin:
        extra_info = json.load(fin)
else:
    extra_info = {}

# Load and merge info at this step
for course_id in extra_info:
    if course_id not in info_dict:
        info_dict[course_id] = extra_info[course_id]
    else:
        # override per-key
        for key in extra_info[course_id]:
            info_dict[course_id][key] = extra_info[course_id][key]

info_list = sorted( tuple(info_dict.items()) )

# TODO: build course URLS like javascript does & augment course_info...
# TODO: Maybe just do that in build.py as well?

result = template.render(
    css=css_code,
    courses=info_list,
    js=js_code
)

with open(result_file, 'w') as fout:
    fout.write(result)
