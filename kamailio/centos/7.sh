#!/usr/bin/env bash

set -x

function install() {
    # Install Dependencies
    yum update -y
    yum groupinstall -y 'core'
    yum groupinstall -y 'base'
    yum groupinstall -y 'Development Tools'
    yum install -y psmisc wget sed gawk vim epel-release

    yum install -y mariadb mariadb-libs mariadb-devel mariadb-server
    ln -s /usr/share/mariadb/ /usr/share/mysql
    # Make sure no extra configs present on fresh install
    rm -f ~/.my.cnf

    # Start MySql
    systemctl start mariadb
    systemctl enable mariadb
    alias mysql="mariadb"

    # Disable SELinux
    sed -i -e 's/(^SELINUX=).*/SELINUX=disabled/' /etc/selinux/config

    # Add the Kamailio repos to yum
    (cat << 'EOF'
[home_kamailio_v5.1.x-rpms]
name=RPM Packages for Kamailio v5.1.x (CentOS_7)
type=rpm-md
baseurl=http://download.opensuse.org/repositories/home:/kamailio:/v5.1.x-rpms/CentOS_7/
gpgcheck=1
gpgkey=http://download.opensuse.org/repositories/home:/kamailio:/v5.1.x-rpms/CentOS_7/repodata/repomd.xml.key
enabled=1
EOF
    ) > /etc/yum.repos.d/kamailio.repo

    yum update -y
    yum install -y kamailio kamailio-ldap kamailio-mysql kamailio-postgres kamailio-debuginfo kamailio-xmpp \
        kamailio-unixodbc kamailio-utils kamailio-tls kamailio-presence kamailio-outbound kamailio-gzcompress


    # TODO: what is this for???
    touch /etc/tmpfiles.d/kamailio.conf
    echo "d /run/kamailio 0750 kamailio kamailio" > /etc/tmpfiles.d/kamailio.conf

    # Configure Kamailio and Required Database Modules
    mkdir -p /etc/kamailio
    echo "" >> /etc/kamailio/kamctlrc
    echo "DBENGINE=MYSQL" >> /etc/kamailio/kamctlrc
    echo "INSTALL_EXTRA_TABLES=yes" >> /etc/kamailio/kamctlrc
    echo "INSTALL_PRESENCE_TABLES=yes" >> /etc/kamailio/kamctlrc
    echo "INSTALL_DBUID_TABLES=yes" >> /etc/kamailio/kamctlrc
    echo "DBROOTUSER=\"${MYSQL_ROOT_USERNAME}\"" >> /etc/kamailio/kamctlrc
    if [[ -z "${MYSQL_ROOT_PASSWORD-unset}" ]]; then
        echo "DBROOTPWSKIP=yes" >> /etc/kamailio/kamctlrc
    else
        echo "DBROOTPW=\"${MYSQL_ROOT_PASSWORD}\"" >> /etc/kamailio/kamctlrc
    fi

    # Will hardcode lation1 as the database character set used to create the Kamailio schema due to
    # a potential bug in how Kamailio additional tables are created
    echo "CHARSET=latin1" >> /etc/kamailio/kamctlrc

    # Execute 'kamdbctl create' to create the Kamailio database schema
    kamdbctl create

    # Setup firewall rules
    firewall-cmd --zone=public --add-port=5060/udp --permanent
    firewall-cmd --zone=public --add-port=10000-30000/udp --permanent
    firewall-cmd --reload

    # TODO: add kamailio logrotate settings
}

function uninstall {
    # Stop servers
    systemctl stop kamailio
    systemctl stop mariadb

    # Backup kamailio configuration directory
    mv -f /etc/kamailio /etc/kamailio.bak.$(date +%Y%m%d_%H%M%S)

    # Backup mysql / mariadb
    mv -f /var/lib/mysql /var/lib/mysql.bak.$(date +%Y%m%d_%H%M%S)

    # Uninstall Kamailio modules and mysql / Mariadb
    yum remove -y mysql\*
    yum remove -y mariadb\*
    yum remove -y kamailio\*
    rm -rf /etc/my.cnf*; rm -f /etc/my.cnf*; rm -f ~/*my.cnf

    # Remove firewall rules that was created by us:
    firewall-cmd --zone=public --remove-port=5060/udp --permanent
    firewall-cmd --zone=public --remove-port=10000-30000/udp --permanent
    firewall-cmd --reload

    # TODO: remove kamailio logrotate settings
}

case "$1" in
    uninstall|remove)
        #Remove Kamailio
        DSIP_PORT=$3
        KAM_VERSION=$2
        $1
        ;;
    install)
        #Install Kamailio
        DSIP_PORT=$3
        KAM_VERSION=$2
        $1
        ;;
    *)
        echo "usage $0 [install <kamailio version> <dsip_port> | uninstall <kamailio version> <dsip_port>]"
        ;;
esac
