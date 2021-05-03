#!/usr/bin/env python

import jinja2
import json
import sys, os

if len(sys.argv) != 8 or '-h' in sys.argv:
    print("Got", len(sys.argv), "arguments...")
    print(
        "Usage: build_alt.py <template> <css> <class_list> <extra_info>"
        " <js> <svg> <output>"
    )
    exit(0)

(
    _,
    template_file,
    css_file,
    class_list,
    extra_info_file,
    js_file,
    svg_file,
    result_file
) = sys.argv

with open(template_file, 'r') as fin:
    template = jinja2.Template(fin.read())

with open(css_file, 'r') as fin:
    css_code = fin.read()

with open(js_file, 'r') as fin:
    js_code = fin.read()

with open(class_list, 'r') as fin:
    cids = fin.read().strip().splitlines()

all_info = {}
for cid in cids:
    info = {'id': cid}
    filename = os.path.join("course_info", cid + ".json")
    if os.path.exists(filename):
        with open(filename, 'r') as fin:
            info = json.load(fin)
    all_info[cid] = info

if os.path.exists(extra_info_file):
    with open(extra_info_file, 'r') as fin:
        extra_info = json.load(fin)
else:
    extra_info = {}

# Load and merge info at this step
for course_id in extra_info:
    if course_id not in all_info:
        all_info[course_id] = extra_info[course_id]
    else:
        # override per-key
        for key in extra_info[course_id]:
            all_info[course_id][key] = extra_info[course_id][key]

info_list = sorted( tuple(all_info.items()) )

with open(svg_file, 'r') as fin:
    svg = fin.read()

# TODO: build course URLS like javascript does & augment course_info...
# TODO: Maybe just do that in build.py as well?

result = template.render(
    css=css_code,
    courses=info_list,
    js=js_code,
    svg=svg
)

with open(result_file, 'w') as fout:
    fout.write(result)
