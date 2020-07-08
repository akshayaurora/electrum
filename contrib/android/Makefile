PYTHON = python3

# needs kivy installed or in PYTHONPATH

.PHONY: theming apk clean

theming:
	#bash -c 'for i in network lightning; do convert -background none theming/light/$i.{svg,png}; done'
	$(PYTHON) -m kivy.atlas ../../electrum/gui/kivy/theming/light 1024 ../../electrum/gui/kivy/theming/light/*.png
trezorlib:
	if [ ! -f "../../../trezor-android/trezor-lib/build/outputs/aar/trezor-lib.aar" ]; then\
		cd ../../..;\
		rm -rf trezor-android;\
		git clone https://github.com/trezor/trezor-android;\
                cd trezor-android;\
                git checkout 7f6125664d2608ae82fd08186c8443f60af55aaf;\
		mv build.sh build.sh.old;\
		echo '#bin/bash\nset e\nIMAGE=trezor-android\n\ndocker build -t "$$IMAGE" .\ndocker run -it -v $$(pwd):/src/:z --user="$$(stat -c "%u:%g" .)" "$$IMAGE" ./gradlew bundleReleaseAar\n' >./build.sh;\
		sudo sh ./build.sh;\
		rm build.sh;\
		mv build.sh.old build.sh;\
	else\
		exit 0;\
	fi
	echo "6814da6051c0e59c1ea8bcedd41d40574e26373e86987f813e028d875de4d932 ../../../trezor-android/trezor-lib/build/outputs/aar/trezor-lib.aar" |sha256sum -c;\
	if [ $$? != 0 ]; then\
		echo 'trezor-lib.aar checksum is not valid, something went wrong!';\
		exit 1;\
	else\
		cp ../../../trezor-android/trezor-lib/build/outputs/trezor-lib.aar ../../bin/;\
	fi
prepare:
	# running pre build setup
	@cp buildozer.spec ../../buildozer.spec
	# copy electrum to main.py
	@cp ../../run_electrum ../../main.py
	@-if [ ! -d "../../.buildozer" ];then \
		cd ../..; buildozer android debug;\
		cp -f blacklist.txt .buildozer/android/platform/python-for-android/src/blacklist.txt;\
		rm -rf ./.buildozer/android/platform/python-for-android/dist;\
	fi
apk:
	@make prepare
	@-cd ../..; buildozer android debug deploy run
	@make clean
release:
	@make prepare
	@-cd ../..; buildozer android release
	@make clean
clean:
	# Cleaning up
	# rename main.py to electrum
	@-rm ../../main.py
	# remove buildozer.spec
	@-rm ../../buildozer.spec
