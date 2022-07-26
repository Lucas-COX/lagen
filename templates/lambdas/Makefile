all: install

apply:
	@{{ env }} terraform apply

build:
	@{{ build_command }}

deploy:	build apply

generate:
	@npx lagen

init:
	@terraform init

install:
	@{{ install_command }}

plan:
	@{{ env }}terraform plan
