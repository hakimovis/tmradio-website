all: build

build:
	python poole.py --build

update: build
	-git pull origin gh-pages
	-git add ..
	-git commit -am "Web site udpdate."
	-git push

serve:
	poole.py --serve
