#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2016 Zomboided
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    Shared code to return info about an IP connection.

import re
import urllib2
import xbmcaddon
import xbmcgui
from libs.utility import debugTrace, infoTrace, errorTrace, ifDebug, newPrint



ip_sources = ["Auto select", "IP-API", "IPInfoDB", "freegeoip.net"]
ip_urls = ["", "http://ip-api.com/json", "http://www.ipinfodb.com/my_ip_location.php", "http://freegeoip.net/json/"] 
LIST_DEFAULT = "0,0,0"

MAX_ERROR = 64

def getIPInfoFrom(source):
    # Generate request to find out where this IP is based
    # Successful return is ip, country, region, city, isp 
    # No info generated from call is "no info", "unknown", "unknown", "unknown", url response
    # Or general error is "error", "error", "error", reason, url response
    link = ""
    try:      
        # Determine the URL, make the call and read the response
        url = getIPSourceURL(source)
        if url == "": return "error", "error", "error", "unknown source", ""
        req = urllib2.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0")
        response = urllib2.urlopen(req)
        link = response.read()
        response.close()

        # Call the right routine to parse the reply using regex.
        # If the website changes, this parsing can fail...sigh
        if source == "IPInfoDB": match = getIPInfoDB(link)
        if source == "IP-API": match = getIPAPI(link)
        if source == "freegeoip.net": match = getFreeGeoIP(link)
        if len(match) > 0:
            recordWorking(source)
            for ip, country, region, city, isp in match:
                return ip, country, region, city, isp
        else:
            recordError(source)
            return "no info", "unknown location", "unknown location", "no matches", link
    except:
        recordError(source)
        return "error", "error", "error", "call failed", link


def getIPAPI(link):
    match = re.compile(ur'"city":"(.*?)".*"country":"(.*?)".*"isp":"(.*?)".*"query":"(.*?)".*"regionName":"(.*?)"').findall(link)
    if len(match) > 0:
        for city, country, isp, ip, region in match:
            return [(ip, country, region, city, isp)]
    else:
        return None           
        
        
def getIPInfoDB(link):
    match = re.compile(ur'<h5>Your IP address.*</h5>.*\s*.*<br>.*IP2Location.*\s*.*\s*<li>IP address.*<strong>(.+?)</strong>.*\s*\s*<li>Country : (.+?) <img.*\s*<li>State.*: (.+?)</li>.*\s*<li>City : (.+?)</li>').findall(link)    
    if len(match) > 0:
        for ip, country, region, city in match:
            return [(ip, country, region, city, "Unknown")]
    else:
        return None

        
def getFreeGeoIP(link):
    match = re.compile(ur'"ip":"(.*?)".*"country_name":"(.*?)".*"region_name":"(.*?).*"city":"(.*?)".*').findall(link)
    if len(match) > 0:
        for ip, country, region, city in match:
            return [(ip, country, region, city, "Unknown")]
    else:
        return None


def isAutoSelect(source):
    if source == ip_sources[0]: return True
    return False

        
def getIPSources():
    return ip_sources


def getIPSourceURL(source):
    i = ip_sources.index(source)
    return ip_urls[i]


def getNextSource(current_source):
    next = ip_sources.index(current_source)
    next = next + 1
    if next == len(ip_sources): next = 1
    # Record that we're using another source
    source = xbmcgui.Window(10000).getProperty("VPN_Manager_Last_IP_Service")
    return ip_sources[next]
    

def recordError(source):
    # Double the error value each time to 64
    i = ip_sources.index(source)
    error = getErrorValue(i)
    if error == 0 : error = 1
    else : error = error * 2
    if error > MAX_ERROR : error = MAX_ERROR
    setErrorValue(i, error)

    
def recordWorking(source):
    i = ip_sources.index(source)
    # If a service works (starts working again), set the error value to 0
    setErrorValue(i, 0)
    working = getWorkingValue(i)
    working = working + 1
    if working > MAX_ERROR : working = 0
    setWorkingValue(i, working)
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_IP_Service", source)


    
def getAutoSource():
    # If the VPN has changed, then reset all the numbers        
    addon = xbmcaddon.Addon("service.vpn.manager")
    last_vpn = addon.getSetting("ip_service_last_vpn")
    current_vpn = addon.getSetting("vpn_provider_validated")
    if (not last_vpn == current_vpn):
        addon.setSetting("ip_service_last_vpn", current_vpn)
        resetIPServices()

    # Get the last source we tried to use from the home window or use the first if this is first time through
    source = xbmcgui.Window(10000).getProperty("VPN_Manager_Last_IP_Service")
    if source == "":
        # Record that we're using the first one
        xbmcgui.Window(10000).setProperty("VPN_Manager_Last_IP_Service", ip_sources[1])
        return ip_sources[1]
    else:
    	index = ip_sources.index(source)
        if index > 1:
            if getWorkingValue(index) >= getErrorValue(index - 1):
                setWorkingValue(index, 0)
                index = index - 1
        return ip_sources[index]


def resetIPServices():
    addon = xbmcaddon.Addon("service.vpn.manager")
    addon.setSetting("ip_service_errors", LIST_DEFAULT)
    addon.setSetting("ip_service_values", LIST_DEFAULT)
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_IP_Service", ip_sources[1])


def getIndex(source):
    return ip_sources.index(source)
    
def getErrorValue(index):
    index -= 1
    errors = xbmcaddon.Addon("service.vpn.manager").getSetting("ip_service_errors")
    if not errors == "":
        list = errors.split(",")
        if not index > len(list):
            return int(list[index])
    return 0
    
    
def setErrorValue(index, value):
    index -= 1
    errors = xbmcaddon.Addon("service.vpn.manager").getSetting("ip_service_errors")    
    if errors == "": errors = LIST_DEFAULT
    list = errors.split(",")
    i = 0
    output = ""
    while i < (len(list)):
        if i > 0: output = output + ","
        if i == index: output = output + str(value)
        else: output = output + str(list[i])
        i += 1
    xbmcaddon.Addon("service.vpn.manager").setSetting("ip_service_errors", output)
    
    
def getWorkingValue(index):
    index -= 1
    values = xbmcaddon.Addon("service.vpn.manager").getSetting("ip_service_values")
    if not values == "":
        list = values.split(",")
        if not index > len(list):
            return int(list[index])
    return 0
    
    
def setWorkingValue(index, value):
    index -= 1
    values = xbmcaddon.Addon("service.vpn.manager").getSetting("ip_service_values")    
    if values == "": values = LIST_DEFAULT
    list = values.split(",")
    i = 0
    output = ""
    while i < (len(list)):
        if i > 0: output = output + ","
        if i == index: output = output + str(value)
        else: output = output + str(list[i])
        i += 1
    xbmcaddon.Addon("service.vpn.manager").setSetting("ip_service_values", output)
    
        