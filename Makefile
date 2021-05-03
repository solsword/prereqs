.PHONY: all
all: prereqs.html

.PHONY: clean
clean:
	rm prereqs.svg classes.lst course_info.json prereqs.html

prereqs.svg: prereqs.dot
	dot -Kdot -Tsvg -o$@ $<

# Note: we don't change the mtime of classes.lst if it hasn't changed,
# which causes this rule to re-run needlessly, but also prevents the
# course_info files from being updated for no good reason.
classes.lst: prereqs.dot
	grep 'label="[^"]' $< | cut -d' ' -f3 > $@.tmp
	if [ -n "`diff -q $@ $@.tmp`" ]; then mv $@.tmp $@; fi

.PHONY: course_info
course_info: classes.lst
	mkdir -p course_info
	./scrape.py $<
	touch $@

# Note: this isn't currently being used, because term info can now be
# scraped from the course browser.
term_info.json: catalog_copy.txt $(wildcard term_info_custom.json)
	cp term_info_custom.json term_info.json || ./extract_term_info.py < $< > $@

prereqs.html: template.html prereqs.css prereqs.js prereqs.svg build.py classes.lst extra_info.json course_info course_info/*
	./build.py \
		template.html \
		prereqs.css \
		classes.lst \
		extra_info.json \
		prereqs.js \
		prereqs.svg \
		$@

# Note that we depend on course_info.json but leave that implicit since
# it's a pain to rebuild.
alt.html: template-alt.html alt.css alt.js prereqs.svg build_alt.py classes.lst extra_info.json course_info course_info/*
	./build.py \
		alt \
		template-alt.html \
		alt.css \
		classes.lst \
		extra_info.json \
		alt.js \
		prereqs.svg \
		alt.html 

index.html: prereqs.html
	cp $< $@
