#!/usr/bin/env python3

"""
scrape.py

Web scraper for Wellesley course browser to get info on course
descriptions, etc.
"""

# built-in modules
import re, json, time, sys

# dependencies
import requests
import bs4

# TODO: Update this!
# Note: This represents different semesters to search in as a cascading
# fallback if we can't find a class description.

CURRENT_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
    "202009", # Fall 2020
    "202102" # Spring 2021
]

PREVIOUS_SEMESTERS = [ # For finding info for courses not taught this year. 
    "202002", # Spring 2020
    "201909", # Fall 2019
]

SEMESTERS = CURRENT_SEMESTERS + PREVIOUS_SEMESTERS
# SEMESTERS = PREVIOUS_SEMESTERS + CURRENT_SEMESTERS

classes = sys.stdin.read().split()

if classes == []:
    print(
        "You must supply a list of class IDs (e.g., cs111) via stdin.",
         file=sys.stderr
    )
    exit(1)

def longest_group(groups):
    grlens = [len(g) for g in groups]
    idx = grlens.index(max(grlens))
    return groups[idx]


front_url = "https://courses.wellesley.edu/"
back_url = "https://courses.wellesley.edu/display_single_course_cb.php"
dc_params = [
    "crn",
    "semester",
    "pe_term",
    "myelement",
    "frame_title",
    "show_locations",
    "subj_code",
    "show_schedules",
    "w_crns",
    "secret",
]
post_params = [
    "crn",
    "semester",
    "pe_term",
    "myelement",
    "frame_title",
    "show_locations",
    "show_schedules",
    "w_crns",
    "secret",
]

output = "course_info.json"

initial_class_set = set(classes)
remaining = set(classes)
found = set()

# Cache essential info in these dictionaries to avoid unnecessary http reqeusts to back_urls
full_info = {} # Stores full info including description for every course
course_names = {} 
instructor_URLs = {} 

def process_course(cid, semester): 
    time.sleep(0.05) # don't crawl too fast
    print("Looking up course '" + cid + "' ...")
    post_data = {
        "submit": "Search",
        "keywords": cid,
        "semester": semester,
        "department_subject": "All",
        "department": "All",
        "subject": "All",
        "faculty": "All",
        "meeting_day": "All",
        "meeting_time": "All",
        "special": "All"
    }
    resp = requests.post(front_url, data=post_data)

    # Use Beautiful Soup to parse the HTML
    soup = bs4.BeautifulSoup(resp.text, 'html.parser')

    listing = soup.find(id="course_listing")
    print('listing: {}'.format(listing))
    entries = listing.find_all(class_="courseitem")
    print('entries: {}'.format(entries))

    # Previous code looked only for a first match
    """
    match = None
    for entry in entries:
        entry_html = str(entry)
        if cid.upper() in entry_html:
           match = entry_html
           break
    if match == None:
        print("Warning: could not find course entry for '{}'.".format(cid))
        continue # used to be in loop; lyn changed loop body to function
    """

    # New code looks for all matches to extract term info and associated instructors:
    matches = [entry for entry in entries if cid.upper() in str(entry)]

    if len(matches) == 0: 
        print("Warning: could not find course entry for '{}'.".format(cid))
        # continue
        return # lyn changed loop cotinue to function return 
    # Invariant: following code executed only if len(matches) >= 1:

    # If 2020-21 semester, parse entries into term/instructor info, also 
    # updating course_names, course_descriptions, instructors along the way.
    # Should also collect full_info for each semester, but current only does that 
    # for first class encountered
    if semester in CURRENT_SEMESTERS: 
        collect_term_info_for_entries(cid, semester, matches)
    else: # must be previous semester 
        first_entry_info = get_entry_info(cid, matches[0])
        collect_detailed_info(cid, semester, first_entry_info)

def collect_term_info_for_entries(cid, semester, entries): 
    '''Only called for current semesters, which have terms'''
    term_info = {}
    for entry in entries:
        entry_info = get_entry_info(cid, entry)
        collect_detailed_info(cid, semester, entry_info) # only does work if necessary
        term = entry_info['term']
        if term not in term_info:
            term_dict = {'lecturers': [], 'lab_instructors': []}
            term_info[term] = term_dict # dict that will map sections to instructors
        else: 
            term_dict = term_info[term]
        section = entry_info['section']
        isRemote = entry_info['remote?']
        instructor = entry_info['instructor']
        instructor_dict = {
            'instructor': instructor, 
            'instructor_URL': instructor_URLs[instructor],
            'remote?': isRemote
            }
        term_dict[section] = instructor_dict
        if (section[0] in ['D', 'L'] # lab/discussion section
            and instructor_dict not in term_dict['lab_instructors']):
            term_dict['lab_instructors'].append(instructor_dict)
        else:
            term_dict['lecturers'].append(instructor_dict)
    full_info_for_course = full_info[cid]
    if 'term_info' not in full_info_for_course:
        full_info_for_course['term_info'] = term_info
    else: 
        full_info_for_course['term_info'].update(term_info) # Add new terms to existing dictionary
        
def get_entry_info(cid, entry): 
    coursename_element = entry.find(class_="coursename_small")
    # Example: 
    # <div class="coursename_small">
    #   <p>Data, Analytics, and Visualization </p>
    #   <span class="professorname">Eni Mustafaraj</span>
    # </div>
    course_name = coursename_element.find('p').contents[0].strip()

    # Assumes a single instructor; will need to update for multiple instructors 
    instructor = coursename_element.find(class_='professorname').contents[0].strip()

    # find info from first displayCourse call 
    dc_calls = re.findall(r"displayCourse\([^)]*\)", str(entry))
    first_call = dc_calls[0]
    print('get_dc_info first_call: {}'.format(first_call))
    argspart = first_call.split('(')[1].split(')')[0]
    argsbits = [
        longest_group(groups).strip()
        for groups in re.findall(
            r'''('[^']*'\s*)|("[^"]*"\s*)|([^'",]+\s*)(?:,|$)''',
            argspart
        )
    ]
    args = [
        arg[1:-1]
            if arg[0] in "'\"" # a quoted string
            else (
                int(arg) # an integer?
                    if arg.isdigit()
                    else '' # give up...
            )
        for arg in argsbits
    ]
    print('args: {}'.format(args))
    # Check length
    if len(args) != len(dc_params):
        print (
            "Warning: Wrong # of args:\n{}\nvs\n{}".format(args, dc_params)
        )

    # Build post data dictionary
    dc_info = { dc_params[i]: args[i] for i in range(len(args)) }
    print('get_entryinfo dc_info {}'.format(dc_info))
    semester = dc_info['semester']
    print('semester {}'.format(semester))
    section, term, isRemote = get_section_and_term(cid, dc_info['crn'])
    print('term {}'.format(term))
    print('section {}'.format(section))
    entry_info = {
        'semester': semester, 
        'term': term, 
        'section': section,
        'course_name': course_name, 
        'instructor': instructor,
        'remote?': isRemote, 
        'dc_info': dc_info
        }
    return entry_info

def get_section_and_term(cid, crn): 
    crn_parts = crn.split('-')
    # Examples: 
    # Regular semester: '27287~202002-CS240L02' => ['27287~202002', 'CS240L02]
    # Semester with terms: 
    #   18244-18245~202009-CS121T1-01 => ['18244', '18245~202009', 'CS121T1', '01']
    #   17041~202009-CS111T1-02-Remote =>['17041~202009', 'CS111T1' '02' 'Remote']
    if len(crn_parts) >= 3:
        if '~' in crn_parts[0]:
            section = crn_parts[2]
            term = crn_parts[1].split(cid.upper())[1]
            isRemote = crn_parts[-1] == 'Remote'
        elif '~' in crn_parts[1]:
            section = crn_parts[3]
            term = crn_parts[2].split(cid.upper())[1]
            isRemote = crn_parts[-1] == 'Remote'
        else:
            print('***get_section_and_term: Unxpected crn format: {}'.format(crn))
            section = None
            term = None
            isRemote = None
    elif len(crn_parts) == 2:
        section = crn_parts[1].split(cid.upper())[1]
        term = None
        isRemote = False
    else: 
        print('***get_section_and_term: Unxpected crn format: {}'.format(crn))
        section = None
        term = None
        isRemote = False
    return section, term, isRemote

def collect_detailed_info(cid, semester, entry_info): 
    instructor = entry_info['instructor']
    if instructor in instructor_URLs and cid in full_info: 
        # Have already cached essential info for course and instructor 
        # no need to do anything more; return early 
        return 
    
    # Extract info for backend request for detailed info
    dc_info = entry_info['dc_info']
    post_data = { param: dc_info[param] for param in post_params }
    print('post_data: {}'.format(post_data))

    time.sleep(0.05) # don't crawl too fast

    # Make backend request
    presp = requests.post(back_url, data=post_data)

    # Use Beautiful Soup to parse the HTML
    soup = bs4.BeautifulSoup(presp.text, 'html.parser')

    # Extract what we're interested in
    prof_nodes = soup.find_all('a', class_="professorname")

    professors = [] 

    for prof_node in prof_nodes:
        print('prof_node: {}'.format(prof_node))
        prof_name = prof_node.get_text().strip()
        prof_URL = "https://courses.wellesley.edu/" + prof_node.get('href')
        if prof_name not in instructor_URLs:
            instructor_URLs[prof_name] = prof_URL
        professors.append([prof_name, prof_URL])

    if cid in full_info: 
        # Have already cached essential info for course; no need to more
        return 

    detail_node = soup.find(class_="coursedetail")

    # Extract subsequent divs that hold course info
    course_info = {
        "course_name": entry_info['course_name'], # lyn added 
        "professors": professors,
        "description": "unknown",
        "semester": semester,
        "term": entry_info['term'], # lyn added
        "section": entry_info['section'], # lyn added 
        "details": "",
        "meeting_info": "",
        "distributions": "",
        "linked_courses": "",
        "prereqs": "",
        "extra_info": [],
    }

    dtext = detail_node.get_text()
    print("  ...found: '" + dtext[:55] + "...")

    extra = []
    first = True
    for child in detail_node.children:
        if isinstance(child, bs4.NavigableString):
            child_str = str(child).strip()
            if len(child_str) == 0:
                continue
        else:
            child_str = child.get_text().strip()

        if first:
            course_info["description"] = child_str
            first = False
            continue

        if (
            child_str.startswith("CRN")
         or child_str.startswith("Credit Hours")
        ):
            course_info["details"] = child_str
        elif child_str.startswith("Meeting Time"):
            course_info["meeting_info"] = child_str
        elif child_str.startswith("Distributions"):
            course_info["distributions"] = child_str
        elif child_str.startswith("Prerequisites"):
            course_info["prereqs"] = child_str
        elif child_str.startswith("Linked Courses"):
            course_info["linked_courses"] = child_str
        elif child_str.startswith("Notes"):
            course_info["notes"] = child_str
        elif not child_str.startswith("ShareThis"):
            course_info["extra_info"].append(child_str)
        # else ignore it

    full_info[cid] = course_info
    found.add(cid)

def process_classes(): 
    global remaining 
    # Try searching in different semesters to see if we can find a
    # description...
    for semester in SEMESTERS:
        print("\nSearching in semester '" + semester + "'...")
        if semester in CURRENT_SEMESTERS:
            for cid in initial_class_set: # Process every course in current semester
                process_course(cid, semester)
        else: 
            remaining -= found
            for cid in remaining: # Process only courses not seen yet. 
                process_course(cid, semester)
    print("...done scraping; writing JSON output.")
    with open(output, 'w') as fout:
        json.dump(full_info, fout, indent=2, sort_keys=True)

process_classes()
