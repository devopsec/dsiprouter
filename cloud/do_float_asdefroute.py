#!/usr/bin/env python3

import requests, subprocess

# NOTE: we are using ipv4

def hasFloatingIp():
    resp = requests.get(
        'http://169.254.169.254/metadata/v1/floating_ip/ipv4/active'
    ).text
    if resp == 'true':
        return True
    return False

def getAnchorGateway():
    return requests.get(
        'http://169.254.169.254/metadata/v1/interfaces/public/0/anchor_ipv4/gateway'
    ).text

def getDefIface():
    result = subprocess.run(
        ['ip', '-4', 'route', 'list', 'scope', 'global'],
        capture_output=True,
        text=True
    )
    route = result.stdout.strip().split('\n')[0]
    found = False
    for route_arg in route.split(' '):
        if found:
            return route_arg
        if route_arg == 'dev':
            found = True

def getDefRoutes():
    result = subprocess.run(
        ['ip', '-4', 'route', 'list', 'scope', 'global'],
        capture_output=True,
        text=True
    )
    routes = result.stdout.strip().split('\n')
    def_routes = []
    for route in routes:
        route_args = route.split(' ')
        if route_args[0] in ('default', '0.0.0.0/0'):
            def_routes.append(route_args)
    return def_routes

def isIpDefRoute(check_ip):
    result = subprocess.run(
        ['ip', '-4', 'route', 'list', 'scope', 'global'],
        capture_output=True,
        text=True
    )
    route = result.stdout.strip().split('\n')[0]
    found = False
    for route_arg in route.split(' '):
        if found and route_arg == check_ip:
            return True
        if route_arg == 'via':
            found = True
    return False

if hasFloatingIp():
    anchor_gw = getAnchorGateway()
    if not isIpDefRoute(anchor_gw):
        def_iface = getDefIface()
        def_routes = getDefRoutes()
        
        for route_args in def_routes:
            subprocess.run(
                ['ip', 'route', 'delete', *route_args],
                stdout=subprocess.DEVNULL
            )
        subprocess.run(
            ['ip', 'route', 'add', 'default', 'via', anchor_gw, 'dev', def_iface],
            stdout=subprocess.DEVNULL
        )

exit(0)

