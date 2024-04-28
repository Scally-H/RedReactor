# MakeFile for the RedReactor RR_Driver
# Designed for the RedReactor Ubuntu RR_Kernel
# Author: Pascal Herczog
# Date	: Apr'24 (c)

all: RR_Driver

# RR_Driver needs to link in compiled ina219 library
RR_Driver: ./build/ina219.o
	@echo Building RR_Driver into /build
	g++ -o ./build/RR_Driver ./build/ina219.o ./RR_Driver.cc

# build with RR_Driver debug output to console
debug: ./build/ina219.o
	@echo Building RR_Driver with DEBUG enabled into /build
	g++ -D DEBUG -o ./build/RR_Driver ./build/ina219.o ./RR_Driver.cc

./build/ina219.o: ./src/ina219.cc
# Source file cloned from https://github.com/regisin/ina219
# Fixed sprintf %f output size warning
# Fixed current > 32767 issue #7
	@echo Compiling ina219 library into /build
	mkdir -p ./build
	g++ -o ./build/ina219.o -c src/ina219.cc

clean:
# Remove build files
	rm -rf ./build/*
