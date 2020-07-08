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
	./scrape.py < classes.lst

prereqs.html: template.html prereqs.css prereqs.js prereqs.svg build.py
	./build.py \
		template.html \
		prereqs.css \
		course_info.json \
		prereqs.js \
		prereqs.svg \
		$@
