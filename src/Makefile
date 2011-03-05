all: build

build:
	python poole.py --build

update: fetch build
	yandex-money-history
	-git add ..
	-git commit -am "Web site udpdate."
	-git push

fetch:
	-git pull origin gh-pages

serve:
	poole.py --serve
