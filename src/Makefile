all: build

build:
	./poole.py --build

update: build
	-git add ..
	-git commit -am "Web site udpdate."
	-git push

serve:
	poole.py --serve
