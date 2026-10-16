SHAWELL_REPO = https://github.com/cem-okulmus/shawell
SHAWELL_SRC = temp/shawell-src

clean:
	rm -f results/*
	rm -f temp/*

# Builds shawell natively into binaries/shawell (requires Go), together with
# the DLV and Oxigraph binaries it needs (fetched by its download_deps.sh)
shawell:
	rm -rf $(SHAWELL_SRC)
	git clone --depth 1 $(SHAWELL_REPO) $(SHAWELL_SRC)
	cd $(SHAWELL_SRC) && CGO_ENABLED=0 go build -trimpath -o shawell . && bash download_deps.sh
	mkdir -p binaries/shawell/bin
	cp $(SHAWELL_SRC)/shawell binaries/shawell/
	cp $(SHAWELL_SRC)/bin/dlv $(SHAWELL_SRC)/bin/oxigraph binaries/shawell/bin/
	rm -rf $(SHAWELL_SRC)

# Alternative: builds the shawell docker image used when binaries/shawell is missing
shawell-docker:
	# shawell's Dockerfile defaults to Go 1.22, but its go.mod requires >= 1.25
	docker build --build-arg GO_VERSION=1.25 -t shawell $(SHAWELL_REPO).git

.PHONY: clean shawell shawell-docker
