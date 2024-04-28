obj-m += redreactor.o

KERN_VER=$(shell uname -r)

all:
	make -C /lib/modules/$(KERN_VER)/build M=$(shell pwd) modules

install:
	make INSTALL_MOD_DIR=kernel/drivers/power/supply -C /lib/modules/$(KERN_VER)/build M=$(shell pwd) modules_install
	depmod -A

clean:
	rm -f *.cmd *.ko *.o Module.symvers modules.order *.mod *.mod.c
