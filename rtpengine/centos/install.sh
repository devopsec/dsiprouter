#!/usr/bin/env bash

# Import dsip_lib utility / shared functions
. ${DSIP_PROJECT_DIR}/dsiprouter/dsip_lib.sh

(( $DEBUG == 1 )) && set -x

#Get CentOS Version
export DISTRO_VER=$(cat /etc/redhat-release | cut -d ' ' -f 4 | cut -d '.' -f 1)

# compile and install rtpengine from RPM's
if [[ "$DISTRO_VER" == "8" ]]; then
function install {

function installKernelDevHeaders {
         local OS_VER="$(cat /etc/redhat-release | cut -d ' ' -f 4)"
         local OS_ARCH="$(uname -m)"
         local OS_KERNEL="$(uname -r)"

         yum --disablerepo='*' --enablerepo=elrepo install -y kernel-devel-${OS_KERNEL} kernel-headers-${OS_KERNEL} ||
         yum install -y https://rpmfind.net/linux/centos/${OS_VER}/updates/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
             https://rpmfind.net/linux/centos/${OS_VER}/updates/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
         yum install -y https://rpmfind.net/linux/centos/${OS_VER}/os/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
             https://rpmfind.net/linux/centos/${OS_VER}/os/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
         yum install -y https://linuxsoft.cern.ch/cern/centos/${OS_VER}/updates/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
             https://linuxsoft.cern.ch/cern/centos/${OS_VER}/updates/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
         yum install -y https://linuxsoft.cern.ch/cern/centos/${OS_VER}/os/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
             https://linuxsoft.cern.ch/cern/centos/${OS_VER}/os/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
         yum install -y http://linuxsoft.cern.ch/cern/centos/${OS_VER}/BaseOS/${OS_ARCH}/os/Packages/kernel-devel-${OS_KERNEL}.rpm \
                        http://linuxsoft.cern.ch/cern/centos/${OS_VER}/BaseOS/${OS_ARCH}/os/Packages/kernel-headers-${OS_KERNEL}.rpm ||
         yum install -y http://linuxsoft.cern.ch/cern/centos/${OS_VER}/BaseOS/${OS_ARCH}/os/images/kernel-devel-${OS_KERNEL}.rpm \
                        http://linuxsoft.cern.ch/cern/centos/${OS_VER}/BaseOS/${OS_ARCH}/os/images/kernel-headers-${OS_KERNEL}.rpm
     }
     
     # Install required libraries
     yum -y install dnf-plugins-core
     yum config-manager --set-enabled PowerTools
     dnf -y install https://download.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
     dnf -y localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
     dnf -y install --nogpgcheck https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
     dnf -y install http://rpmfind.net/linux/epel/7/x86_64/Packages/s/SDL2-2.0.10-1.el7.x86_64.rpm
     dnf -y install ffmpeg
     dnf -y install ffmpeg-devel
     yum -y install mysql-devel
     yum -y install iptables-devel kernel-devel kernel-headers xmlrpc-c xmlrpc-c-client
     yum -y install kernel-devel
     yum -y install glib2 glib2-devel gcc zlib zlib-devel openssl openssl-devel pcre pcre-devel libcurl libcurl-devel xmlrpc-c-devel
     yum -y install libevent-devel glib2-devel json-glib-devel gperf gperftools-libs gperftools gperftools-devel libpcap libpcap-devel git hiredis hiredis-devel redis perl-IPC-Cmd
     yum -y install spandsp-devel spandsp
     yum -y install epel-release
     yum -y install elfutils-libelf-devel gcc-toolset-9-elfutils-libelf-devel
     rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
     rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-1.el7.nux.noarch.rpm

     installKernelDevHeaders
     
     # Make and Configure RTPEngine
     cd /usr/local/src
     rm -rf rtpengine/
     git clone https://github.com/sipwise/rtpengine.git -b mr7.5.4
     cd /usr/local/src/rtpengine/daemon/
     make
     cp rtpengine /usr/sbin/rtpengine
     cd /usr/local/src/rtpengine/iptables-extension
     make all
     cp libxt_RTPENGINE.so /usr/lib64/xtables/.
     
     # ensure config dirs exist
     mkdir -p /var/run/rtpengine ${SYSTEM_RTPENGINE_CONFIG_DIR}
     chown -R rtpengine:rtpengine /var/run/rtpengine
     
     # Configure RTPEngine to support kernel packet forwarding
     cd /usr/local/src/rtpengine/kernel-module
     make
     mkdir /lib/modules/$(uname -r)/extra
     cp xt_RTPENGINE.ko /lib/modules/$(uname -r)/extra/xt_RTPENGINE.ko
     
     # Remove RTPEngine kernel module if previously inserted
     if lsmod | grep 'xt_RTPENGINE'; then
         rmmod xt_RTPENGINE
     fi
     # Load new RTPEngine kernel module
     depmod -a
     modprobe xt_RTPENGINE
     
     echo 'add 0' > /proc/rtpengine/control
     iptables -I INPUT -p udp -j RTPENGINE --id 0
     ip6tables -I INPUT -p udp -j RTPENGINE --id 0

     if [ "$SERVERNAT" == "0" ]; then
          INTERFACE=$EXTERNAL_IP
     else
          INTERFACE=$INTERNAL_IP!$EXTERNAL_IP
     fi

    # rtpengine config file
    # set table = 0 for kernel packet forwarding
    (cat << EOF
[rtpengine]
table = -1
interface = ${INTERFACE}
listen-ng = 127.0.0.1:7722
port-min = ${RTP_PORT_MIN}
port-max = ${RTP_PORT_MAX}
log-level = 7
log-facility = local1
log-facility-cdr = local1
log-facility-rtcp = local1
EOF
    ) > ${SYSTEM_RTPENGINE_CONFIG_FILE}

    # setup rtpengine defaults file
    (cat << 'EOF'
RUN_RTPENGINE=yes
CONFIG_FILE=/etc/rtpengine/rtpengine.conf
# CONFIG_SECTION=rtpengine
PIDFILE=/var/run/rtpengine/rtpengine.pid
MANAGE_IPTABLES=yes
TABLE=0
SET_USER=rtpengine
SET_GROUP=rtpengine
LOG_STDERR=yes
EOF
    ) > /etc/default/rtpengine.conf

    # Enable and start firewalld if not already running
    systemctl enable firewalld
    systemctl start firewalld

    # Fix for bug: https://bugzilla.redhat.com/show_bug.cgi?id=1575845
    if (( $? != 0 )); then
        systemctl restart dbus
        systemctl restart firewalld
    fi

    # Setup Firewall rules for RTPEngine
    firewall-cmd --zone=public --add-port=${RTP_PORT_MIN}-${RTP_PORT_MAX}/udp --permanent
    firewall-cmd --reload

    # Setup RTPEngine Logging
    cp -f ${DSIP_PROJECT_DIR}/resources/syslog/rtpengine.conf /etc/rsyslog.d/rtpengine.conf
    touch /var/log/rtpengine.log
    systemctl restart rsyslog

    # Setup logrotate
    cp -f ${DSIP_PROJECT_DIR}/resources/logrotate/rtpengine /etc/logrotate.d/rtpengine

    # Setup Firewall rules for RTPEngine
    firewall-cmd --zone=public --add-port=${RTP_PORT_MIN}-${RTP_PORT_MAX}/udp --permanent
    firewall-cmd --reload

    # Setup tmp files
    echo "d /var/run/rtpengine.pid  0755 rtpengine rtpengine - -" > /etc/tmpfiles.d/rtpengine.conf
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine.service /etc/systemd/system/rtpengine.service
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine-start-pre /usr/sbin/
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine-stop-post /usr/sbin/
    chmod +x /usr/sbin/rtpengine*

    # Reload systemd configs
    systemctl daemon-reload
    # Enable the RTPEngine to start during boot
    systemctl enable rtpengine
    # Start RTPEngine
    systemctl start rtpengine

    # Start manually if the service fails to start
    if [ $? -ne 0 ]; then
        /usr/sbin/rtpengine --config-file=${SYSTEM_RTPENGINE_CONFIG_FILE} --pidfile=/var/run/rtpengine/rtpengine.pid
    fi

    # File to signify that the install happened
    if [ $? -eq 0 ]; then
        touch ${DSIP_PROJECT_DIR}/.rtpengineinstalled
        echo "RTPEngine has been installed!"
    else
        echo "FAILED: RTPEngine could not be installed!"
    fi
}

elif [[ "$DISTRO_VER" == "7" ]]; then
function install {
    local VERSION_NUM=""

    # try installing in the following order:
    # 1: headers from repos
    # 2: headers from rpmfind.net (updates branch)
    # 3: headers from rpmfind.net (os branch)
    # 4: headers from linuxsoft.cern.ch (updates branch)
    # 5: headers from linuxsoft.cern.ch (os branch)
    function installKernelDevHeaders {
        local OS_VER="$(cat /etc/redhat-release | cut -d ' ' -f 4)"
        local OS_ARCH="$(uname -m)"
        local OS_KERNEL="$(uname -r)"

        yum install -y kernel-devel-${OS_KERNEL} kernel-headers-${OS_KERNEL} ||
        yum install -y https://rpmfind.net/linux/centos/7/updates/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
            https://rpmfind.net/linux/centos/7/updates/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
        yum install -y https://rpmfind.net/linux/centos/7/os/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
            https://rpmfind.net/linux/centos/7/os/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
        yum install -y https://linuxsoft.cern.ch/cern/centos/7/updates/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
            https://linuxsoft.cern.ch/cern/centos/7/updates/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm ||
        yum install -y https://linuxsoft.cern.ch/cern/centos/7/os/${OS_ARCH}/Packages/kernel-devel-${OS_KERNEL}.rpm \
            https://linuxsoft.cern.ch/cern/centos/7/os/${OS_ARCH}/Packages/kernel-headers-${OS_KERNEL}.rpm
    }

    # Install required libraries
    yum install -y epel-release
    yum install -y logrotate rsyslog bc
    rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
    rpm -Uh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm
    yum install -y gcc glib2 glib2-devel zlib zlib-devel openssl openssl-devel pcre pcre-devel libcurl libcurl-devel \
        xmlrpc-c xmlrpc-c-devel libpcap libpcap-devel hiredis hiredis-devel json-glib json-glib-devel libevent libevent-devel \
        iptables-devel xmlrpc-c-devel ffmpeg ffmpeg-devel gperf redhat-lsb iptables-ipv6 nc dkms perl perl-IPC-Cmd spandsp-devel
    yum install -y redhat-rpm-config rpm-build pkgconfig

    installKernelDevHeaders

    if [ $? -ne 0 ]; then
        echo "Problem with installing the required libraries for RTPEngine"
        exit 1
    fi

    # alias and link rsyslog to syslog service as in debian
    # allowing rsyslog to be accessible via syslog namespace
    # the settings are already there just commented out by default
    sed -i -r 's|^[;#](.*)|\1|g' /usr/lib/systemd/system/rsyslog.service
    ln -s /usr/lib/systemd/system/rsyslog.service /etc/systemd/system/syslog.service
    systemctl daemon-reload

    # create rtpengine user and group
    # sometimes locks aren't properly removed (this seems to happen often on VM's)
    rm -f /etc/passwd.lock /etc/shadow.lock /etc/group.lock /etc/gshadow.lock
    useradd --system --user-group --shell /bin/false --comment "RTPengine RTP Proxy" rtpengine

    # Make and Configure RTPEngine
    cd ${SRC_DIR}
    rm -rf rtpengine.bak 2>/dev/null
    mv -f rtpengine rtpengine.bak 2>/dev/null
    git clone https://github.com/sipwise/rtpengine.git -b ${RTPENGINE_VER}
    cd ./rtpengine

    VERSION_NUM=$(grep -oP 'Version:.+?\K[\w\.\~\+]+' ./el/rtpengine.spec)
    if (( $(echo "$RTPENGINE_VER" | perl -0777 -pe 's|mr(\d+\.\d+)\.(\d+)\.(\d+)|\1\2\3 >= 6.511|gm' | bc -l) )); then
        PREFIX="rtpengine-${VERSION_NUM}/"
    else
        PREFIX="ngcp-rtpengine-${VERSION_NUM}/"
    fi

    mkdir -p ~/rpmbuild/SOURCES

    git archive --output ~/rpmbuild/SOURCES/ngcp-rtpengine-${VERSION_NUM}.tar.gz --prefix=${PREFIX} ${RTPENGINE_VER}
    rpmbuild -ba  ./el/rtpengine.spec
    rpm -i ~/rpmbuild/RPMS/$(uname -m)/ngcp-rtpengine-${VERSION_NUM}*.rpm
    rpm -q ngcp-rtpengine >/dev/null 2>&1; ret=$?
    rpm -i ~/rpmbuild/RPMS/noarch/ngcp-rtpengine-dkms-${VERSION_NUM}*.rpm
    rpm -q ngcp-rtpengine-dkms >/dev/null 2>&1; ((ret+=$?))
    rpm -i ~/rpmbuild/RPMS/$(uname -m)/ngcp-rtpengine-kernel-${VERSION_NUM}*.rpm
    rpm -q ngcp-rtpengine-kernel >/dev/null 2>&1; ((ret+=$?))
    if [ -f ~/rpmbuild/RPMS/$(uname -m)/ngcp-rtpengine-recording-${VERSION_NUM}*.rpm ]; then
        rpm -i ~/rpmbuild/RPMS/$(uname -m)/ngcp-rtpengine-recording-${VERSION_NUM}*.rpm
        rpm -q ngcp-rtpengine-recording >/dev/null 2>&1; ((ret+=$?))
    fi

    if [ $ret -ne 0 ]; then
        echo "Problem installing RTPEngine RPM's"
        exit 1
    fi

    # ensure config dirs exist
    mkdir -p /var/run/rtpengine ${SYSTEM_RTPENGINE_CONFIG_DIR}
    chown -R rtpengine:rtpengine /var/run/rtpengine


    # Configure RTPEngine to support kernel packet forwarding
    cd ${SRC_DIR}/rtpengine/kernel-module &&
    make &&
    cp -f xt_RTPENGINE.ko /lib/modules/$(uname -r)/updates/ &&
    if [ $? -ne 0 ]; then
        echo "Problem installing RTPEngine kernel-module"
        exit 1
    fi

    # Remove RTPEngine kernel module if previously inserted
    if lsmod | grep 'xt_RTPENGINE'; then
        rmmod xt_RTPENGINE
    fi
    # Load new RTPEngine kernel module
    depmod -a &&
    modprobe xt_RTPENGINE


    if [ "$SERVERNAT" == "0" ]; then
        INTERFACE=$EXTERNAL_IP
    else
        INTERFACE=$INTERNAL_IP!$EXTERNAL_IP
    fi

    # rtpengine config file
    # set table = 0 for kernel packet forwarding
    (cat << EOF
[rtpengine]
table = -1
interface = ${INTERFACE}
listen-ng = 127.0.0.1:7722
port-min = ${RTP_PORT_MIN}
port-max = ${RTP_PORT_MAX}
log-level = 7
log-facility = local1
log-facility-cdr = local1
log-facility-rtcp = local1
EOF
    ) > ${SYSTEM_RTPENGINE_CONFIG_FILE}

    # setup rtpengine defaults file
    (cat << 'EOF'
RUN_RTPENGINE=yes
CONFIG_FILE=/etc/rtpengine/rtpengine.conf
# CONFIG_SECTION=rtpengine
PIDFILE=/var/run/rtpengine/rtpengine.pid
MANAGE_IPTABLES=yes
TABLE=0
SET_USER=rtpengine
SET_GROUP=rtpengine
LOG_STDERR=yes
EOF
    ) > /etc/default/rtpengine.conf

    # Enable and start firewalld if not already running
    systemctl enable firewalld
    systemctl start firewalld

    # Fix for bug: https://bugzilla.redhat.com/show_bug.cgi?id=1575845
    if (( $? != 0 )); then
        systemctl restart dbus
        systemctl restart firewalld
    fi

    # Setup Firewall rules for RTPEngine
    firewall-cmd --zone=public --add-port=${RTP_PORT_MIN}-${RTP_PORT_MAX}/udp --permanent
    firewall-cmd --reload

    # Setup RTPEngine Logging
    cp -f ${DSIP_PROJECT_DIR}/resources/syslog/rtpengine.conf /etc/rsyslog.d/rtpengine.conf
    touch /var/log/rtpengine.log
    systemctl restart rsyslog

    # Setup logrotate
    cp -f ${DSIP_PROJECT_DIR}/resources/logrotate/rtpengine /etc/logrotate.d/rtpengine

    # Setup Firewall rules for RTPEngine
    firewall-cmd --zone=public --add-port=${RTP_PORT_MIN}-${RTP_PORT_MAX}/udp --permanent
    firewall-cmd --reload

    # Setup tmp files
    echo "d /var/run/rtpengine.pid  0755 rtpengine rtpengine - -" > /etc/tmpfiles.d/rtpengine.conf
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine.service /etc/systemd/system/rtpengine.service
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine-start-pre /usr/sbin/
    cp -f ${DSIP_PROJECT_DIR}/rtpengine/rtpengine-stop-post /usr/sbin/
    chmod +x /usr/sbin/rtpengine*

    # Reload systemd configs
    systemctl daemon-reload
    # Enable the RTPEngine to start during boot
    systemctl enable rtpengine
    # Start RTPEngine
    systemctl start rtpengine

    # Start manually if the service fails to start
    if [ $? -ne 0 ]; then
        /usr/sbin/rtpengine --config-file=${SYSTEM_RTPENGINE_CONFIG_FILE} --pidfile=/var/run/rtpengine/rtpengine.pid
    fi

    # File to signify that the install happened
    if [ $? -eq 0 ]; then
        touch ${DSIP_PROJECT_DIR}/.rtpengineinstalled
        echo "RTPEngine has been installed!"
    else
        echo "FAILED: RTPEngine could not be installed!"
    fi
}
else
echo "Invalid CentOS Version"
fi
    
# Remove RTPEngine
function uninstall {
    systemctl stop rtpengine
    rm -f /usr/sbin/rtpengine
    rm -f /etc/rsyslog.d/rtpengine.conf
    rm -f /etc/logrotate.d/rtpengine
    echo "Removed RTPEngine for $DISTRO"
}

case "$1" in
    uninstall|remove)
        uninstall && exit 0
        ;;
    install)
        install && exit 0
        ;;
    *)
        printerr "usage $0 [install | uninstall]" && exit 1
        ;;
esac

