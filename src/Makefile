all: build

build:
	poole.py --build

update: build
	-git add -A
	-git commit -am "Web site udpdate."
	-git push

serve:
	poole.py --serve
