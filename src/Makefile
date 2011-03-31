all: build

build:
	python poole.py --build
	-git add ..

update: fetch update-money build
	-git commit -a
	-git push

update-podcasts: fetch build
	-git add -A
	-git commit -am "Обновление подкастов (автомат)."
	-git push

update-map: fetch build
	-git add -A
	-git commit -am "Обновление карты (автомат)."
	-git push

autoupdate: fetch build
	-git add -A
	-git commit -am "Обновление сайта (автомат)."
	-git push

update-money:
	-yandex-money-history

fetch:
	-git pull origin gh-pages

serve:
	poole.py --serve

tsn:
	$(EDITOR) `ls input/programs/tsn/*/index.md | sort | tail -1`
