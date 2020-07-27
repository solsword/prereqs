#!/usr/bin/env python3

"""
extract_term_info.py

Script to look at catalog copy text for the department and extract which
classes are being taught in which semesters for a given catalog year.
Takes catalog copy on stdin and prints out json listing which courses are
taught in which semesters. The resulting json is a mapping from semester
IDs to lists of course IDs taught in that semester.

Assumes that each class block starts with "Course ID:" and eventually has
the text "Semesters Offered this Academic Year:" or the text "Not offered
in"

NOTE: The catalog copy is not trustworthy! In particular, it may list
some classes as "not offered" that actually are being offered as
circumstances change, and it is not necessarily updated when the course
browser is updated!
"""

import sys, re, json

copy = sys.stdin.read()

years_match = re.search(r"Catalog Year: (\d+)-(\d+)", copy)
years = years_match.groups()
fall_tag = "fall" + years[0]
spring_tag = "spring" + years[1]

bits = copy.split("Course ID:")

course_bits = [
    bit.strip()
    for bit in bits
    if (
        "Semesters Offered this Academic Year:" in bit
     or "Not offered in" in bit
    )
]

in_fall = set()
in_spring = set()
neither = set()

for cb in course_bits:
    course_id = cb.split()[0].lower().split('/')[0]
    not_offered = "Not offered in" in cb
    if not_offered:
        neither.add(course_id)
    else:
        offered_match = re.search(
            r"Semesters Offered this Academic Year: ([^:]*)",
            cb
        )
        if "Fall" in offered_match.groups()[0]:
            in_fall.add(course_id)
        if "Spring" in offered_match.groups()[0]:
            in_spring.add(course_id)

# Note; for now we ignore the 'neither' set...

result = {
    fall_tag: sorted(in_fall),
    spring_tag: sorted(in_spring),
}

print(json.dumps(result, indent=2))
