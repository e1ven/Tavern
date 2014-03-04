"""
A python version of http://user-agent-string.info/download/UASparser
Customized to use Tavern primitives.
Edited by Hicro Kee (http://hicrokee.com) and http://molhanec.net (Michal Molhanec) Colin Davis (E1ven.com)

>>> import libtavern.uasparser
>>> uas = libtavern.uasparser.UASparser()
>>> test = ['SonyEricssonK750i/R1L Browser/SEMC-Browser/4.2 Profile/MIDP-2.0 Configuration/CLDC-1.1',
... 'Mozilla/5.0 (Windows; U; Windows NT 5.2; en-GB; rv:1.8.1.18) Gecko/20081029 Firefox/2.0.0.18',
... 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_5; en-us) AppleWebKit/525.26.2 (KHTML, like Gecko) Version/3.2 Safari/525.26.12',
... ]
>>> for item in test:
...    res = uas.parse(item)
...    print(res['typ'] +" " + res['ua_name'] + " " + res['os_name'])
Mobile Browser SEMC Browser 4.2 JVM (Java)
Browser Firefox 2.0.0.18 Windows 2003 Server
Browser Safari 3.2 OS X 10.5 Leopard
"""

import os

import urllib.request
import urllib.error
import urllib.parse
import re
import time
import libtavern.baseobj

class UASException(Exception):
    pass


class UASparser(libtavern.baseobj.Baseobj):

    def __init2__(self):
        self.ini_file = 'datafiles/useragent.ini'
        self.cache_data = None
        self.info_url = '/useragent/'
        self.os_img_url = '/useragent/img/%s'
        self.ua_img_url = '/useragent/img/%s'

    # @libtavern.utils.memorise(parent_keys=['ua_img_url', 'os_img_url', 'info_url'], ttl=self.server.serversettings.settings['cache']['uasparser']['seconds'], maxsize=self.server.serversettings.settings['cache']['uasparser']['size'])
    def parse(self, useragent, entire_url=''):
        """
        Get the information of an useragent string.
        Args:
            useragent: String, an useragent string
            entire_url: String, write the key labels which you want to get an entire url split by comma, expected 'ua_icon' or 'os_icon'.
        """
        ret = {
            'typ': 'unknown',
            'ua_family': 'unknown',
            'ua_name': 'unknown',
            'ua_url': 'unknown',
            'ua_company': 'unknown',
            'ua_company_url': 'unknown',
            'ua_icon': 'unknown.png',
            'ua_info_url': 'unknown',
            'os_family': 'unknown',
            'os_name': 'unknown',
            'os_url': 'unknown',
            'os_company': 'unknown',
            'os_company_url': 'unknown',
            'os_icon': 'unknown.png',
            'ua_versions': ['unknown', 0, 0]
        }

        os_index = ['os_family', 'os_name', 'os_url', 'os_company',
                    'os_company_url', 'os_icon']
        ua_index = ['ua_family', 'ua_name', 'ua_url', 'ua_company',
                    'ua_company_url', 'ua_icon', '', 'ua_info_url']

        if 'ua_icon' in entire_url:
            ret['ua_icon'] = self.ua_img_url % ret['ua_icon']
        if 'os_icon' in entire_url:
            ret['os_icon'] = self.os_img_url % ret['os_icon']

        def toPythonReg(reg):
            reg_l = reg[1:reg.rfind('/')]  # modify the re into python format
            reg_r = reg[reg.rfind('/') + 1:]
            flag = 0
            if 's' in reg_r:
                flag = flag | re.S
            if 'i' in reg_r:
                flag = flag | re.I
            return re.compile(reg_l, flag)

        # Check argument
        if not useragent:
            raise UASException("Excepted argument useragent is not given.")

        # Load cache data
        data = self.loadData()

        # Is it a spider?
        for index in data['robots']['order']:
            test = data['robots'][index]
            if test[0] == useragent:
                ret['typ'] = 'Robot'
                for i in range(1, len(test) + 1):  # fill out the structure.
                    if i < 6:
                        ret[ua_index[i - 1]] = test[i]
                    elif i == 6:
                        ret[ua_index[i - 1]] = (
                            'ua_icon' in entire_url and self.ua_img_url or "%s") % test[i]
                    elif i == 7:
                        if test[7]:  # OS detail
                            for j in range(1, len(data['os'][int(test[7])])):
                                ret[os_index[j]] = data['os'][int(test[7])][j]
                    elif i == 8:
                        ret[ua_index[i - 1]
                            ] = ''.join([self.info_url, test[i]])

                return ret

        # A browser
        id_browser = None
        for index in data['browser_reg']['order']:
            test = data['browser_reg'][index]
            test_rg = toPythonReg(test[0]).findall(
                useragent)  # All regular expression should be in python format
            if test_rg:
                id_browser = int(test[1])  # Bingo
                info = test_rg[0]
                break

        # Get broser detail
        if id_browser:
            _index = ['ua_family', 'ua_url', 'ua_company',
                      'ua_company_url', 'ua_icon', 'ua_info_url']
            try:
                # Any better method to figure out it?
                if id_browser in data['browser']:
                    for i in range(1, len(data['browser'][id_browser]) + 1):
                        if i <= 4:
                            ret[_index[i - 1]] = data['browser'][id_browser][i]
                        elif i == 5:
                            ret[_index[i - 1]] = ('ua_icon' in entire_url and self.ua_img_url or "%s") % data[
                                'browser'][id_browser][i]
                        else:
                            ret[_index[i - 1]] = "".join(
                                [self.info_url, data['browser'][id_browser][i]])
            except:
                pass

            try:
                ret['typ'] = data['browser_type'][int(
                    data['browser'][id_browser][0])][0]
                ret['ua_name'] = "%s %s" % (
                    data['browser'][id_browser][1], info)
            except:
                pass

        # Get OS detail
        if id_browser in data['browser_os']:
            try:
                os_id = int(data['browser_os'][id_browser][0])
                for i in range(0, len(data['os'][os_id])):
                    if i < 5:
                        ret[os_index[i]] = data['os'][os_id][i]
                    else:
                        ret[os_index[i]] = (
                            'os_icon' in entire_url and self.os_img_url or "%s") % data['os'][os_id][i]
                return ret
            except:
                pass

        # Try to match an OS
        os_id = None
        for index in data['os_reg']['order']:
            test = data['os_reg'][index]
            test_rg = toPythonReg(test[0]).findall(useragent)
            if test_rg:
                os_id = int(test[1])
                break

        # Get OS detail
        if os_id and os_id in data['os']:
            for i in range(0, len(data['os'][os_id])):
                if i < 5:
                    ret[os_index[i]] = data['os'][os_id][i]
                else:
                    ret[os_index[i]] = (
                        'os_icon' in entire_url and self.os_img_url or "%s") % data['os'][os_id][i]

        # Clean up some stuff the root library doesn't detect
        if ret['ua_name'] is not None:
            result = re.findall("\d+\.?\d*", ret['ua_name'])
            if len(result) > 0:
                ret['ua_version'] = result[0]
            else:
                ret['ua_version'] = '0.0.0'
            result = re.findall('[^\[\]]+', ret['ua_name'])

        if ret['ua_version'] is not None:
            versions = []
            for i in ret['ua_version'].split('.'):
                try:
                    versions.append(int(i))
                except:
                    pass
            ret['ua_versions'] = versions

        return ret

    def _parseIniFile(self, file):
        """Parse an ini file into a dictionary structure."""
        data = {}
        current_section = 'unknown'
        section_pat = re.compile(r'^\[(\S+)\]$')
        option_pat = re.compile(r'^(\d+)\[\]\s=\s"(.*)"$')

        # step by line
        for line in file:
            option = option_pat.findall(line)
            if option:  # do something for option
                key = int(option[0][0])
                if key in data[current_section]:
                    data[current_section][key].append(option[0][1])
                else:
                    data[current_section][key] = [option[0][1], ]
                    data[current_section]['order'].append(key)
            else:
                section = section_pat.findall(line)  # do something for section
                if section:
                    current_section = section[0]
                    data[current_section] = {'order': []}
        return data

    def loadData(self):
        """Load cache data."""

        if self.cache_data:  # no need to load
            return self.cache_data

        with open(self.ini_file, 'r', encoding='utf-8') as cache_file:
            self.cache_data = self._parseIniFile(cache_file)

        return self.cache_data
