#!/usr/bin/env bash

# set project dir (where src files are located)
export DSIP_PROJECT_DIR=${DSIP_PROJECT_DIR:-/opt/dsiprouter}
# import dsip_lib utility / shared functions
if [[ "$DSIP_LIB_IMPORTED" != "1" ]]; then
    . ${DSIP_PROJECT_DIR}/dsiprouter/dsip_lib.sh
fi

printdbg 'verifying version requirements'
REPO_URL='https://github.com/dOpensource/dsiprouter.git'
UPGRADE_VER=$(jq -r -e '.version' <"$(dirname "$(dirname "$(readlink -f "$0")")")/settings.json")
UPGRADE_VER_TAG="v${UPGRADE_VER}-rel"
CURRENT_VERSION=$(getConfigAttrib "VERSION" "/etc/dsiprouter/gui/settings.py")
UPGRADE_DEPENDS=( $(jq -r -e '.depends[]' <"$(dirname "$(dirname "$(readlink -f "$0")")")/settings.json") )
(
    for VER in ${UPGRADE_DEPENDS[@]}; do
        if [[ "$CURRENT_VERSION" == "$VER" ]]; then
            exit 0
        fi
    done
    exit 1
) || {
    printerr "unsupported upgrade scenario ($CURRENT_VERSION -> $UPGRADE_VER)"
    exit 1
}

printdbg 'backing up configs just in case the upgrade fails'
BACKUP_DIR="/var/backups"
CURR_BACKUP_DIR="${BACKUP_DIR}/$(date '+%s')"
mkdir -p ${CURR_BACKUP_DIR}/{opt/dsiprouter,var/lib/mysql,${HOME},etc/dsiprouter,etc/kamailio,etc/rtpengine,etc/systemd/system,lib/systemd/system,etc/default}
cp -rf /opt/dsiprouter/. ${CURR_BACKUP_DIR}/opt/dsiprouter/
cp -rf /etc/kamailio/. ${CURR_BACKUP_DIR}/etc/kamailio/
cp -rf /var/lib/mysql/. ${CURR_BACKUP_DIR}/var/lib/mysql/
cp -f /etc/my.cnf ${CURR_BACKUP_DIR}/etc/ 2>/dev/null
cp -rf /etc/mysql/. ${CURR_BACKUP_DIR}/etc/mysql/
cp -f ${HOME}/.my.cnf ${CURR_BACKUP_DIR}/${HOME}/ 2>/dev/null
cp -f /etc/systemd/system/{dnsmasq.service,kamailio.service,nginx.service,rtpengine.service} ${CURR_BACKUP_DIR}/etc/systemd/system/
cp -f /lib/systemd/system/dsiprouter.service ${CURR_BACKUP_DIR}/lib/systemd/system/
cp -f /etc/default/kamailio ${CURR_BACKUP_DIR}/etc/default/
printdbg "files were backed up here: ${CURR_BACKUP_DIR}/"

printdbg 'retrieving system info'
export DISTRO=$(getDistroName)
export DISTRO_VER=$(getDistroVer)
export DISTRO_MAJOR_VER=$(cut -d '.' -f 1 <<<"$DISTRO_VER")
export DISTRO_MINOR_VER=$(cut -s -d '.' -f 2 <<<"$DISTRO_VER")

printdbg 'retrieving DB connection settings'
export KAM_DB_HOST=$(getConfigAttrib "KAM_DB_HOST" "/etc/dsiprouter/gui/settings.py")
export KAM_DB_PORT=$(getConfigAttrib "KAM_DB_PORT" "/etc/dsiprouter/gui/settings.py")
export KAM_DB_NAME=$(getConfigAttrib "KAM_DB_NAME" "/etc/dsiprouter/gui/settings.py")
export ROOT_DB_USER=$(getConfigAttrib "ROOT_DB_USER" "/etc/dsiprouter/gui/settings.py")
export ROOT_DB_PASS=$(decryptConfigAttrib "ROOT_DB_PASS" "/etc/dsiprouter/gui/settings.py")

printdbg 'configuring dSIPRouter project files'
# fresh repo coming up
rm -rf /opt/dsiprouter
git clone --depth 1 -b "$UPGRADE_VER_TAG" "$REPO_URL" /opt/dsiprouter
export DSIP_PROJECT_DIR=/opt/dsiprouter

printdbg 'migrating database schema'
(
cat <<'EOF'
ALTER TABLE address
  MODIFY COLUMN `ip_addr` VARCHAR(253) NOT NULL,
  MODIFY COLUMN `tag` VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE dr_gateways
  MODIFY COLUMN `address` VARCHAR(253) NOT NULL,
  MODIFY COLUMN `pri_prefix` VARCHAR(64) NOT NULL DEFAULT '',
  MODIFY COLUMN `attrs` VARCHAR(255) NOT NULL DEFAULT '',
  MODIFY COLUMN `description` VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE dsip_settings CONVERT TO CHARACTER SET utf8mb4;

ALTER TABLE uacreg
  MODIFY COLUMN `l_domain` VARCHAR(253) NOT NULL DEFAULT '',
  MODIFY COLUMN `r_domain` VARCHAR(253) NOT NULL DEFAULT '',
  MODIFY COLUMN `realm` varchar(253) NOT NULL DEFAULT '',
  MODIFY COLUMN `auth_proxy` varchar(16000) NOT NULL DEFAULT '';
EOF
) | sqlAsTransaction --user="$ROOT_DB_USER" --password="$ROOT_DB_PASS" --host="$KAM_DB_HOST" --port="$KAM_DB_PORT"

if (( $? != 0 )); then
    printerr 'Failed merging DB schema'
    exit 1
fi

printdbg 'updating dsiprouter settings'
setConfigAttrib 'VERSION' '0.73' /etc/dsiprouter/gui/settings.py &&
dsiprouter updatedsipconfig

printdbg 'generating documentation for the GUI'
(
    cd ${DSIP_PROJECT_DIR}/docs
    make html >/dev/null 2>&1
)

printdbg 'updating dSIPRouter CLI'
ln -sf ${DSIP_PROJECT_DIR}/dsiprouter.sh /usr/bin/dsiprouter
if [[ -f /etc/bash.bashrc ]]; then
    perl -i -0777 -pe 's%#(if ! shopt -oq posix; then\n)#([ \t]+if \[ -f /usr/share/bash-completion/bash_completion \]; then\n)#(.*?\n)#(.*?\n)#(.*?\n)#(.*?\n)#(.*?\n)%\1\2\3\4\5\6\7%s' /etc/bash.bashrc
fi
cp -f ${DSIP_PROJECT_DIR}/dsiprouter/dsip_completion.sh /etc/bash_completion.d/dsiprouter
touch /etc/dsiprouter/.dsiproutercliinstalled

printdbg 'generating documentation for the CLI'
cp -f ${DSIP_PROJECT_DIR}/resources/man/dsiprouter.1 /usr/share/man/man1/
gzip -f /usr/share/man/man1/dsiprouter.1
mandb
cp -f ${DSIP_PROJECT_DIR}/dsiprouter/dsip_completion.sh /etc/bash_completion.d/dsiprouter

printdbg 'upgrading DNSmasq installation'
(
    DNSMASQ_LISTEN_ADDRS="127.0.0.1"
    DNSMASQ_NAME_SERVERS=("nameserver 127.0.0.1")

    # get dynamic network settings
    NETWORK_MODE=${NETWORK_MODE:-$(getConfigAttrib 'NETWORK_MODE' ${DSIP_CONFIG_FILE})}
    NETWORK_MODE=${NETWORK_MODE:-0}
    if (( $NETWORK_MODE == 0 )); then
        export INTERNAL_IP_ADDR=$(getInternalIP -4)
        export INTERNAL_IP_NET=$(getInternalCIDR -4)
        export INTERNAL_IP6_ADDR=$(getInternalIP -6)
        export INTERNAL_IP_NET6=$(getInternalCIDR -6)

        EXTERNAL_IP_ADDR=$(getExternalIP -4)
        export EXTERNAL_IP_ADDR=${EXTERNAL_IP_ADDR:-$INTERNAL_IP_ADDR}
        EXTERNAL_IP6_ADDR=$(getExternalIP -6)
        export EXTERNAL_IP6_ADDR=${EXTERNAL_IP6_ADDR:-$INTERNAL_IP6_ADDR}

        export INTERNAL_FQDN=$(getInternalFQDN)
        export EXTERNAL_FQDN=$(getExternalFQDN)
        if [[ -z "$EXTERNAL_FQDN" ]] || ! checkConn "$EXTERNAL_FQDN"; then
            export EXTERNAL_FQDN="$INTERNAL_FQDN"
        fi
    elif (( $NETWORK_MODE == 1 )); then
        export INTERNAL_IP_ADDR=${INTERNAL_IP_ADDR:-$(getConfigAttrib 'INTERNAL_IP_ADDR' ${DSIP_CONFIG_FILE})}
        export INTERNAL_IP_NET=${INTERNAL_IP_NET:-$(getConfigAttrib 'INTERNAL_IP_NET' ${DSIP_CONFIG_FILE})}
        export INTERNAL_IP6_ADDR=${INTERNAL_IP6_ADDR:-$(getConfigAttrib 'INTERNAL_IP6_ADDR' ${DSIP_CONFIG_FILE})}
        export INTERNAL_IP_NET6=${INTERNAL_IP_NET6:-$(getConfigAttrib 'INTERNAL_IP_NET6' ${DSIP_CONFIG_FILE})}

        export EXTERNAL_IP_ADDR=${EXTERNAL_IP_ADDR:-$(getConfigAttrib 'EXTERNAL_IP_ADDR' ${DSIP_CONFIG_FILE})}
        export EXTERNAL_IP6_ADDR=${EXTERNAL_IP6_ADDR:-$(getConfigAttrib 'EXTERNAL_IP6_ADDR' ${DSIP_CONFIG_FILE})}

        export INTERNAL_FQDN=${INTERNAL_FQDN:-$(getConfigAttrib 'INTERNAL_FQDN' ${DSIP_CONFIG_FILE})}
        export EXTERNAL_FQDN=${EXTERNAL_FQDN:-$(getConfigAttrib 'EXTERNAL_FQDN' ${DSIP_CONFIG_FILE})}
    elif (( $NETWORK_MODE == 2 )); then
        PUBLIC_IFACE=${PUBLIC_IFACE:-$(getConfigAttrib 'PUBLIC_IFACE' ${DSIP_CONFIG_FILE})}
        PRIVATE_IFACE=${PRIVATE_IFACE:-$(getConfigAttrib 'PRIVATE_IFACE' ${DSIP_CONFIG_FILE})}

        export INTERNAL_IP_ADDR=$(getIP -4 "$PRIVATE_IFACE")
        export INTERNAL_IP_NET=$(getInternalCIDR -4 "$PRIVATE_IFACE")
        export INTERNAL_IP6_ADDR=$(getIP -6 "$PRIVATE_IFACE")
        export INTERNAL_IP_NET6=$(getInternalCIDR -6 "$PRIVATE_IFACE")

        EXTERNAL_IP_ADDR=$(getIP -4 "$PUBLIC_IFACE")
        export EXTERNAL_IP_ADDR=${EXTERNAL_IP_ADDR:-$INTERNAL_IP_ADDR}
        EXTERNAL_IP6_ADDR=$(getIP -6 "$PUBLIC_IFACE")
        export EXTERNAL_IP6_ADDR=${EXTERNAL_IP6_ADDR:-$INTERNAL_IP6_ADDR}

        export INTERNAL_FQDN=$(getInternalFQDN)
        export EXTERNAL_FQDN=$(getExternalFQDN)
        if [[ -z "$EXTERNAL_FQDN" ]] || ! checkConn "$EXTERNAL_FQDN"; then
            export EXTERNAL_FQDN="$INTERNAL_FQDN"
        fi
    else
        printerr 'Network Mode is invalid, can not proceed any further'
        exit 1
    fi

    # create dnsmasq user and group
    # output removed, some cloud providers (DO) use caching and output is misleading
    # sometimes locks aren't properly removed (this seems to happen often on VM's)
    rm -f /etc/passwd.lock /etc/shadow.lock /etc/group.lock /etc/gshadow.lock &>/dev/null
    userdel dnsmasq &>/dev/null; groupdel dnsmasq &>/dev/null
    useradd --system --user-group --shell /bin/false --comment "DNSmasq DNS Resolver" dnsmasq &>/dev/null

    # install dnsmasq
    if cmdExists 'apt-get'; then
        apt-get install -y dnsmasq
    elif cmdExists 'yum'; then
        yum install -y dnsmasq
    fi

    # make sure run dir is created
    mkdir -p /run/dnsmasq
    chown -R dnsmasq:dnsmasq /run/dnsmasq

    # integration for resolvconf / systemd-resolvd
    if systemctl -q is-enabled resolvconf; then
        DNSMASQ_RESOLV_FILE="/run/dnsmasq/resolv.conf"

        cat <<'EOF' >/etc/default/resolvconf
REPORT_ABSENT_SYMLINK=no
TRUNCATE_NAMESERVER_LIST_AFTER_LOOPBACK_ADDRESS=yes
EOF


        cat <<'EOF' >/etc/resolvconf/update.d/zz_dnsmasq
#!/bin/sh
#
# Script to update the resolver list for dnsmasq
#
# N.B. Resolvconf may run us even if dnsmasq is not (yet) running.
# If dnsmasq is installed then we go ahead and update the resolver list
# in case dnsmasq is started later.
#
# Assumption: On entry, PWD contains the resolv.conf-type files.
#
# This is a modified version of the file from the dnsmasq package.
#

set -e

RUN_DIR="/run/dnsmasq"
RSLVRLIST_FILE="${RUN_DIR}/resolv.conf"
TMP_FILE="${RSLVRLIST_FILE}_new.$$"
MY_NAME_FOR_RESOLVCONF="dnsmasq"
RESOLVCONF_GEN_FILE="/run/resolvconf/resolv.conf"

[ -x /usr/sbin/dnsmasq ] || exit 0
[ -x /lib/resolvconf/list-records ] || exit 1

PATH=/bin:/sbin

report_err() { echo "$0: Error: $*" >&2 ; }

# Stores arguments (minus duplicates) in RSLT, separated by spaces
# Doesn't work properly if an argument itself contains whitespace
uniquify() {
	RSLT=""
	while [ "$1" ] ; do
		for E in $RSLT ; do
			[ "$1" = "$E" ] && { shift ; continue 2 ; }
		done
		RSLT="${RSLT:+$RSLT }$1"
		shift
	done
}

filterdnsmasq() {
    while read ADDR; do
        for DNSMASQ_ADDR in $@; do
            [ "x$ADDR" = "x$DNSMASQ_ADDR" ] && continue 2
        done
        echo "$ADDR"
    done
}

if [ ! -d "$RUN_DIR" ] && ! mkdir --parents --mode=0755 "$RUN_DIR" ; then
	report_err "Failed trying to create directory $RUN_DIR"
	exit 1
fi

RSLVCNFFILES="$RESOLVCONF_GEN_FILE"
for F in $(/lib/resolvconf/list-records) ; do
	case "$F" in
	    "lo.$MY_NAME_FOR_RESOLVCONF")
		DNSMASQ_ADDRS="$(sed -n -e 's/^[[:space:]]*nameserver[[:space:]]\+//p' lo.$MY_NAME_FOR_RESOLVCONF)"
		;;
	  *)
		RSLVCNFFILES="${RSLVCNFFILES:+$RSLVCNFFILES }$F"
		;;
	esac
done

NMSRVRS=""
if [ "$RSLVCNFFILES" ] ; then
	uniquify $(
	    sed -n -e 's/^[[:space:]]*nameserver[[:space:]]\+//p' $RSLVCNFFILES |
	    filterdnsmasq $DNSMASQ_ADDRS
    )
	NMSRVRS="$RSLT"
fi

# Dnsmasq uses the mtime of $RSLVRLIST_FILE, with a resolution of one second,
# to detect changes in the file. This means that if a resolvconf update occurs
# within one second of the previous one then dnsmasq may fail to notice the
# more recent change. To work around this problem we sleep one second here
# if necessary in order to ensure that the new mtime is different.
if [ -f "$RSLVRLIST_FILE" ] && [ "$(ls -go --time-style='+%s' "$RSLVRLIST_FILE" | { read p h s t n ; echo "$t" ; })" = "$(date +%s)" ] ; then
	sleep 1
fi

clean_up() { rm -f "$TMP_FILE" ; }
trap clean_up EXIT
: >| "$TMP_FILE"
for N in $NMSRVRS ; do echo "nameserver $N" >> "$TMP_FILE" ; done
mv -f "$TMP_FILE" "$RSLVRLIST_FILE"

EOF
        chmod +x /etc/resolvconf/update.d/zz_dnsmasq
        rm -f /etc/resolvconf/update.d/dnsmasq

        rm -f /etc/resolv.conf
        echo '# DNS servers are being managed by dnsmasq, DO NOT CHANGE THIS FILE' >/etc/resolv.conf
        for NAME_SERVER in ${DNSMASQ_NAME_SERVERS[@]}; do
            echo "$NAME_SERVER" >>/etc/resolv.conf
        done

        # update the dynamic resolv.conf files
        resolvconf -u

    # static resolv.conf
    else
        DNSMASQ_RESOLV_FILE="/etc/resolv.conf"

        if ! grep -q -E 'nameserver 127\.0\.0\.1|nameserver ::1' /etc/resolv.conf 2>/dev/null; then
            # extra check in case no nameserver found
            if ! grep -q 'nameserver' /etc/resolv.conf 2>/dev/null; then
                joinwith '' $'\n' '' "${DNSMASQ_NAME_SERVERS[@]}" >> /etc/resolv.conf
            else
                sed -i -r "0,\|^nameserver.*|{s||$(joinwith '' '' '\n' "${DNSMASQ_NAME_SERVERS[@]}")&|}" /etc/resolv.conf
            fi
        fi
    fi

    # dnsmasq configuration
    mv -f /etc/dnsmasq.conf /etc/dnsmasq.conf.bak 2>/dev/null
    cat << EOF >/etc/dnsmasq.conf
port=53
domain-needed
bogus-priv
strict-order
listen-address=${DNSMASQ_LISTEN_ADDRS}
bind-interfaces
user=dnsmasq
group=dnsmasq
conf-file=/etc/dnsmasq.conf
resolv-file=${DNSMASQ_RESOLV_FILE}
pid-file=/run/dnsmasq/dnsmasq.pid
EOF

    # setup hosts in cluster node is resolvable
    # cron and kam service will configure these dynamically
    if grep -q 'DSIP_CONFIG_START' /etc/hosts 2>/dev/null; then
        perl -e "\$int_ip='${INTERNAL_IP_ADDR}'; \$ext_ip='${EXTERNAL_IP_ADDR}'; \$int_fqdn='${INTERNAL_FQDN}'; \$ext_fqdn='${EXTERNAL_FQDN}';" \
            -0777 -i -pe 's|(#+DSIP_CONFIG_START).*?(#+DSIP_CONFIG_END)|\1\n${int_ip} ${int_fqdn} local.cluster\n${ext_ip} ${ext_fqdn} local.cluster\n\2|gms' /etc/hosts
    else
        printf '\n%s\n%s\n%s\n%s\n' \
            '#####DSIP_CONFIG_START' \
            "${INTERNAL_IP_ADDR} ${INTERNAL_FQDN} local.cluster" \
            "${EXTERNAL_IP_ADDR} ${EXTERNAL_FQDN} local.cluster" \
            '#####DSIP_CONFIG_END' >> /etc/hosts
    fi

    # configure systemd service
    case "$DISTRO" in
        debian|ubuntu)
            cat << 'EOF' >/etc/systemd/system/dnsmasq.service
[Unit]
Description=dnsmasq - A lightweight DHCP and caching DNS server
Requires=basic.target network.target
After=network.target network-online.target basic.target
Wants=nss-lookup.target
Before=nss-lookup.target
DefaultDependencies=no

[Service]
Type=forking
PIDFile=/run/dnsmasq/dnsmasq.pid
Environment='RUN_DIR=/run/dnsmasq'
Environment='IGNORE_RESOLVCONF=yes'
# make sure everything is setup correctly before starting
ExecStartPre=!-/usr/bin/dsiprouter chown -dnsmasq
ExecStartPre=/usr/sbin/dnsmasq --test
# We run dnsmasq via the /etc/init.d/dnsmasq script which acts as a
# wrapper picking up extra configuration files and then execs dnsmasq
# itself, when called with the "systemd-exec" function.
ExecStart=/etc/init.d/dnsmasq systemd-exec
# The systemd-*-resolvconf functions configure (and deconfigure)
# resolvconf to work with the dnsmasq DNS server. They're called like
# this to get correct error handling (ie don't start-resolvconf if the
# dnsmasq daemon fails to start.
ExecStartPost=/etc/init.d/dnsmasq systemd-start-resolvconf
ExecStop=/etc/init.d/dnsmasq systemd-stop-resolvconf
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
EOF
            ;;
        almalinux|rocky)
            cat << 'EOF' >/etc/systemd/system/dnsmasq.service
[Unit]
Description=dnsmasq - A lightweight DHCP and caching DNS server
Requires=basic.target network.target
After=network.target network-online.target basic.target
Before=multi-user.target
DefaultDependencies=no

[Service]
Type=simple
PIDFile=/run/dnsmasq/dnsmasq.pid
Environment='RUN_DIR=/run/dnsmasq'
# make sure everything is setup correctly before starting
ExecStartPre=!-/usr/bin/dsiprouter chown -dnsmasq
ExecStartPre=/usr/sbin/dnsmasq --test
ExecStart=/usr/sbin/dnsmasq -k
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
EOF
            ;;
        # amazon linux 2 and rhel 8 ship with systemd ver 219 (many new features missing)
        # therefore we have to create backward compatible versions of our service files
        # the following snippet may be useful in the future when we support later versions
        #SYSTEMD_VER=$(systemctl --version | head -1 | awk '{print $2}')
        # TODO: the same issue occurs on debian9 with systemd ver 232
        amzn|rhel)
            cat << 'EOF' >/etc/systemd/system/dnsmasq.service
[Unit]
Description=dnsmasq - A lightweight DHCP and caching DNS server
Requires=basic.target network.target
After=network.target network-online.target basic.target
Before=multi-user.target
DefaultDependencies=no

[Service]
Type=simple
PermissionsStartOnly=true
PIDFile=/run/dnsmasq/dnsmasq.pid
Environment='RUN_DIR=/run/dnsmasq'
# make sure everything is setup correctly before starting
ExecStartPre=/usr/bin/dsiprouter chown -dnsmasq
ExecStartPre=/usr/sbin/dnsmasq --test
ExecStart=/usr/sbin/dnsmasq -k
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
EOF
            ;;
    esac

    # reload systemd configs and start on boot
    systemctl daemon-reload
    systemctl enable dnsmasq

    # update DNS hosts prior to dSIPRouter startup
    addInitCmd "${DSIP_PROJECT_DIR}/dsiprouter.sh updatednsconfig"
    # update DNS hosts every minute
    if ! crontab -l 2>/dev/null | grep -q "${DSIP_PROJECT_DIR}/dsiprouter.sh updatednsconfig"; then
        cronAppend "0 * * * * ${DSIP_PROJECT_DIR}/dsiprouter.sh updatednsconfig"
    fi

    systemctl restart dnsmasq
    if systemctl is-active --quiet dnsmasq; then
        touch /etc/dsiprouter/.dnsmasqinstalled
        exit 0
    else
        exit 1
    fi
)

if (( $? != 0 )); then
    printerr 'Failed upgrading DNSmasq'
    exit 1
fi

printdbg 'upgrading kamailio configs'
dsiprouter configurekam

printdbg 'updating file permissions'
dsiprouter chown

printdbg 'restarting services'
systemctl restart kamailio
systemctl restart nginx
systemctl restart dsiprouter

exit 0