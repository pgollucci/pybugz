release:
	sed -i '' -e "s,__version__ =.*,__version__ = '${VERSION}'," bugz/__init__.py
	git add bugz/__init__.py
	git commit -m "Tag ${VERSION}"
	git tag ${VERSION}
	git push --tags
	git push

.PHONY: release
