CUR_DIR=$(shell pwd)
NPM_CMD?=install

.PHONY: docker-npm
docker-npm:
	docker run \
		-v $(CUR_DIR):/throat \
		-w /throat node:14-buster-slim \
		npm $(NPM_CMD)

.PHONY: docker-compose-build
docker-compose-build:
	docker compose build
	@$(DONE)

.PHONY: up
up: docker-compose-build
	docker compose up --remove-orphans -d
	@$(DONE)

.PHONY: down
down:
	docker compose down --remove-orphans
	@$(DONE)

.PHONY: docker-shell
docker-shell: docker-compose-build
	docker-compose run --rm throat /bin/bash
	@$(DONE)

.PHONY: test
test: docker-compose-build
	docker compose up --detach redis
	docker compose run \
		--name=throat_tests \
		--rm \
		--no-deps \
		--volume $(CUR_DIR)/test:/throat/test \
		-e TEST_CONFIG=/throat/test/test_config_docker_compose.yaml \
		throat \
		pytest $(ARGS)
	@$(DONE)
