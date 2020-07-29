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
