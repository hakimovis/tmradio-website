all: build

build:
	python poole.py --build

update: fetch update-money build
	-git add ..
	-git commit -a
	-git push

update-podcasts: fetch build
	-git add -A
	-git commit -am "Обновление подкастов (автомат)."
	-git push

update-money:
	-yandex-money-history

fetch:
	-git pull origin gh-pages

serve:
	poole.py --serve
