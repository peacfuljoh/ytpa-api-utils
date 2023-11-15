SHELL = /bin/bash
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

REPO_NAME_ = ytpa_api_utils
REPO_NAME_GHA_ = ytpa-api-utils

REPO_ROOT_ = /home/nuc/$(REPO_NAME_)
BB_ROOT_ = $(REPO_ROOT_)
REPO_ROOT_GHA_ = /home/runner/work/$(REPO_NAME_GHA_)/$(REPO_NAME_GHA_)
BB_ROOT_GHA_ = $(REPO_ROOT_GHA_)

ACT_ENV = $(CONDA_ACTIVATE) $(REPO_NAME_)
PYPI_PKG_VER_CMD = $$($(ACT_ENV) && poetry search $(REPO_NAME_) | grep -E '$(REPO_NAME_)' | grep -oP '\(\K[^\)]+')
LOCAL_PKG_VER_CMD = $$($(ACT_ENV) && poetry version | grep -Po '(?<=$(REPO_NAME_) )[^;]+')


build:
	cd $(BB_ROOT_)
	conda env update --file environment.yml --prune
	echo 'export PYTHONPATH="${PYTHONPATH}:$(BB_ROOT_)"' >> ~/.bashrc

build-gha:
	echo 'PYTHONPATH=$(BB_ROOT_GHA_)' >> $(GITHUB_ENV)

test:
	$(CONDA_ACTIVATE) $(REPO_NAME_) && \
	cd $(BB_ROOT_) && \
	pytest

test-gha:
	$(CONDA_ACTIVATE) $(REPO_NAME_) && \
	cd $(BB_ROOT_GHA_) && \
	pytest

coverage:
	$(CONDA_ACTIVATE) $(REPO_NAME_) && \
	cd $(BB_ROOT_) && \
	coverage run -m pytest && \
	coverage report

publish:
	$(eval PYPI_PKG_VER_=$(shell echo $(PYPI_PKG_VER_CMD)))
	$(eval LOCAL_PKG_VER_=$(shell echo $(LOCAL_PKG_VER_CMD)))
	@if [ $(PYPI_PKG_VER_) != $(LOCAL_PKG_VER_) ]; then \
		echo Upgrading package from '$(PYPI_PKG_VER_)' to '$(LOCAL_PKG_VER_)' && \
		$(ACT_ENV) && \
		poetry build && \
		poetry publish --username="__token__" --password=$(PYPI_PASSWORD); \
	else \
		echo "Package '$(REPO_NAME_)' is up-to-date."; \
	fi
