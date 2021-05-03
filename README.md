# `prereqs`

Code for taking a hand-curated .dot file and using Graphviz to build a
diagram of course dependencies. Scraping code for Wellesley's course
browser is included to get course descriptions. Use `make` to build
`prereqs.html` which is a single-file bundle that includes everything you
need to display the courses.

## Dependencies

- `make` (or you could open the makefile and run those commands yourself)
- Graphviz (command-line interface)
    * Seems like something around 2.40 is required, and at least 2.30
      definitely doesn't work (doesn't support custom CSS classes for
      nodes/edges)
- Python packages `requests` and `bs4`

## How To

1. Edit prereqs.dot: add new courses and/or dependencies there, specify
   which classes are being offered, and which semesters they're being
   offered in. Fiddle with rank=same specifications to try to get the
   layout looking reasonable (good luck!). Use constraint=false to let
   edges route a long way, which can also be helpful in this process.
   At this stage, you're running `make prereqs.svg` and refreshing that
   SVG in your web browser to get things looking good.
2. Run `make index.html` and pray. If you're lucky, scrape.py will just
   work... If you're unlucky, you'll have to figure out what changes have
   been made to the course browser and debug scrape.py. Note that if the
   list of classes has not changed, you may have to "touch classes.lst"
   to force `make course_info` to actually update stuff, since by default
   it doesn't do that as the scraping process takes a while. On the other
   hand, if you want to avoid re-scraping, just `touch course_info/*` so
   that those .json files are newer than `classes.lst` (the scraper has
   its own built-in logic for this).


