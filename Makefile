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

prereqs.html: template.html prereqs.css prereqs.js prereqs.svg build.py course_info.json extra_info.json
	./build.py \
		template.html \
		prereqs.css \
		course_info.json \
		extra_info.json \
		prereqs.js \
		prereqs.svg \
		$@

index.html: prereqs.html
	cp $< $@
