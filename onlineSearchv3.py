"""
    Purpose:  Used to tranlsate installed software to CPE23 format data
    Reason :  Because I don't want to pay any money for buying related product (we don't have enought money) !!
"""

import requests
import json
import random
import re
import pandas as pd

from datetime import datetime
random.seed(datetime.now())


def cjk_detect(texts):
    # korean
    if re.search("[\uac00-\ud7a3]", texts):
        return "ko"
    # japanese
    if re.search("[\u3040-\u30ff]", texts):
        return "ja"
    # chinese
    if re.search("[\u4e00-\u9FFF]", texts):
        return "zh"
    return None



nist_cpe_api = "https://services.nvd.nist.gov/rest/json/cpes/1.0"

xls_filename = "Upload_Template_1090901.xls"
xls = pd.read_excel(xls_filename, converters = {'資產名稱': str, '資產版本':str})

for i in range(len(xls.index)):
    cName = str(xls.loc[i]['資產廠商']).lower()
    if cName == "nan":
        cName = ""
    pName = str(xls.loc[i]['資產名稱']).lower()
    ver   = str(xls.loc[i]['資產版本'])
    if ver == "nan":
        ver = ""
    if ver.find("("):
        nver = re.sub('\s\(.*\)', '', ver)
    else:
        nver = ver
    # if pName contains CJK, directly shows no cpe!
    if cjk_detect(cName) is not None or cjk_detect(pName) is not None:
        print("%s,%s" % (pName, " no cpe!"))
        xls.iloc[i, 6] = "N/A"
        xls.iloc[i, 7] = "N/A"
        continue

    # max try 3 times, by pName
    pNameAr = pName.split()
    lName = len(pNameAr)
    # some variables
    maxMatch = 0
    tmpCPE = []

    for j in range(4):
        # first try, condition: cName, 1 word; pName, all; ver, all.
        if cName not in pName:
            keyword = "{} {} {}".format(cName.split()[0], ' '.join(pName.split()[:lName]), nver)
        else:
            keyword = "{} {}".format(' '.join(pName.split()[:lName]), nver)
        #print("use: ", keyword)

        
        # use api from nvd site.
        keyWords = keyword.split()
        my_params = {'keyword': keyword}
        r = requests.get(nist_cpe_api, params = my_params)
        if r.status_code == requests.codes.ok:
            j = json.loads(r.text)
            if j["totalResults"] > 0:
                    for c in j["result"]["cpes"]:
                        # compare which match count would be the most.
                        tmpTitle = set(c["titles"][0]["title"].lower().replace("(", " ").replace(")", " ").split())
                        tmpMaxMatch = len(tmpTitle.intersection(set(keyWords)))
                        if tmpMaxMatch > maxMatch:
                            tmpCPE = c
                            maxMatch = tmpMaxMatch
        
        # check time to break
        if bool(tmpCPE):
            break

        lName -= 1
        if lName < 2:
            break
    
    # final try, only use pNamr
    if not bool(tmpCPE):
        keyWords = pNameAr
        #print("use: ", pName)
        my_params = {'keyword': pName}
        r = requests.get(nist_cpe_api, params = my_params)
        if r.status_code == requests.codes.ok:
            j = json.loads(r.text)
            if j["totalResults"] > 0:
                    for c in j["result"]["cpes"]:
                        # compare which match count would be the most.
                        tmpTitle = set(c["titles"][0]["title"].lower().replace("(", " ").replace(")", " ").split())
                        tmpMaxMatch = len(tmpTitle.intersection(set(keyWords)))
                        if tmpMaxMatch > maxMatch:
                            tmpCPE = c
                            maxMatch = tmpMaxMatch

    # show the result and save to a new xls file.
    if bool(tmpCPE):
        print("%s,%s" % (keyword, tmpCPE["cpe23Uri"]))
        xls.iloc[i, 6] = tmpCPE["cpe23Uri"]
        xls.iloc[i, 7] = tmpCPE["titles"][0]["title"]
    else:
        print("%s,%s" % (keyword, " no cpe!"))
        xls.iloc[i, 6] = "N/A"
        xls.iloc[i, 7] = "N/A"

xls.to_excel("final.xls")
print("finish!")