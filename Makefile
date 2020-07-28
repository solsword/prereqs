.PHONY: all
all: prereqs.html

.PHONY: clean
clean:
	rm prereqs.svg classes.lst course_info.json prereqs.html

prereqs.svg: prereqs.dot
	dot -Kdot -Tsvg -o$@ $<

classes.lst: prereqs.dot
	grep 'label="[^"]' $< | cut -d' ' -f3 > $@

course_info.json: classes.lst
	./scrape.py < $<

term_info.json: catalog_copy.txt $(wildcard term_info_custom.json)
	cp term_info_custom.json term_info.json || ./extract_term_info.py < $< > $@

# Note that we depend on course_info.json but leave that implicit since
# it's a pain to rebuild.
prereqs.html: template.html prereqs.css prereqs.js prereqs.svg build.py extra_info.json
	./build.py \
		template.html \
		prereqs.css \
		course_info.json \
		extra_info.json \
		prereqs.js \
		prereqs.svg \
		$@

# Note that we depend on course_info.json but leave that implicit since
# it's a pain to rebuild.
alt.html: template-alt.html alt.css alt.js build_alt.py extra_info.json
	./build_alt.py \
		template-alt.html \
		alt.css \
		course_info.json \
		extra_info.json \
		alt.js \
		alt.html 
