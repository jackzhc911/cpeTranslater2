"""
    Version:  0.1
    Purpose:  used to query cpe by company name, product title and version.
    Todo   :  add input txt file, transfer and output to txt file.
"""
import time
import argparse
import os
from sys import exit

import sqlite3
from sqlite3 import Error

import csv
import re

#----------------------------------------------------------------------
g_dbfile = "cpe_lite.db"
g_cpe_filename = "official-cpe-dictionary_v2.3.xml"
#----------------------------------------------------------------------
def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        #print(sqlite3.version)
    except Error as e:
        print(e)

    return conn

def executeSQL(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def initDB():
    sql_create_cpe_table = """ CREATE TABLE IF NOT EXISTS projects (
                                        cpe23 text PRIMARY KEY,
                                        companyName text NOT NULL,
                                        title text
                                    ); """
    conn = create_connection(g_dbfile)
    # create tables
    if conn is not None:
        # create projects table
        executeSQL(conn, sql_create_cpe_table)

        conn.close()
    else:
        print("Error! cannot create the database connection.")

def clearData():
    print("clear data")
    sql_del_all_data = """ DELETE FROM projects """
    conn = create_connection(g_dbfile)
    # create tables
    if conn is not None:
        # clear projects table's data
        executeSQL(conn, sql_del_all_data)

        conn.close()
    else:
        print("Error! cannot create the database connection.")

def importXML(cpe_filename):
    try:
        from xml.etree import cElementTree as ET
    except ImportError:
        from xml.etree import ElementTree as ET

    try:
        print("[*] Loading XML CPE file.")
        root = ET.parse(cpe_filename).getroot()
    except ET.ParseError as e:
        print("[!] Error while parsing CPE dictionary: Error: %s" % e.message)
        exit(1)

    conn = create_connection(g_dbfile)
    cursorObj = conn.cursor()
    data = []

    print("[*] Converting XML to CPE database.")
    for item in root.getchildren()[1:]:
        #tmpCPE23 = item.getchildren()[2].attrib['name']
        tmpCPE23 = item.find('{http://scap.nist.gov/schema/cpe-extension/2.3}cpe23-item').attrib['name']
        tmpCompany = tmpCPE23.split(":")[3]
        #tmpTitle = item.getchildren()[0].text
        tmpTitle = item.find('./{http://cpe.mitre.org/dictionary/2.0}title[@{http://www.w3.org/XML/1998/namespace}lang="en-US"]').text

        data.append((tmpCPE23, tmpCompany, tmpTitle))
    
    cursorObj.executemany("INSERT INTO projects VALUES(?, ?, ?)", data)
    conn.commit()

    conn.close()
    

    

def update_db():
    """
    This function download, parse and update cpe.db.
    """
    if g_dbfile not in os.listdir():
        # create db file
        initDB()
        print("create db done.")
    else:
        # update db file
        clearData()
        importXML(g_cpe_filename)
        print("update db done.")


def test_db():
    conn = create_connection(g_dbfile)
    cursorObj = conn.cursor()
    cursorObj.execute('SELECT * FROM projects WHERE companyName="microsoft"')
    rows = cursorObj.fetchall()
    for row in rows:
        print(row)

    conn.close()

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

def search_cpe(company, title, version):
    conn = create_connection(g_dbfile)
    cursorObj = conn.cursor()

    if company is None:
        cursorObj.execute('SELECT * FROM projects WHERE title like ?', ('%'+title+'%',))
    else:
        cursorObj.execute('SELECT * FROM projects WHERE companyName=? AND title like ?', (company, '%'+title+'%'))

    rows = cursorObj.fetchall()
    for row in rows:
        if version in row[2].lower():
            print(row)

    conn.close()

def fetch_data_by(vender, sw_name, version):
    conn = create_connection(g_dbfile)
    cursorObj = conn.cursor()

    if vender == "":
        cursorObj.execute('SELECT * FROM projects WHERE title like ?', ('%'+sw_name+'%',))
    else:
        cursorObj.execute('SELECT * FROM projects WHERE companyName=? AND title like ?', (vender, '%'+sw_name+'%'))

    rows = cursorObj.fetchall()

    if len(rows)>0:
        return rows
    else:
        return None

    conn.close()

def batch_search(in_file, out_file):
    # format: sw_name, version, vender
    lol = list(csv.reader(open(in_file, 'r', encoding='utf-8'), delimiter=','))
    lwl = []

    for l in lol:
        sw_name = l[0].lower()
        version = l[1].lower()
        vender  = l[2].lower()
        # don't handle CJK
        if cjk_detect(sw_name) is not None or cjk_detect(vender) is not None:
            print("%s,%s" % (sw_name, " no cpe!"))
            l.append("N/A")
            lwl.append(l)
            continue

        # make vender name shorter
        # 1: HP
        vender = "hp" if vender == 'Hewlett-Packard' else vender
        # 2: other
        if len(vender.split())>1:
            vender = vender.split()[0]

        # preventing product name from vender name then trim leading whitespace
        sw_name = sw_name.lower().replace(vender, "").lstrip(' ')
        
        # Step 1: use sw_name, vender to query and grep by version
        #print("+--------------------------------------------------------------------+")
        #print("> ", vender, sw_name, version)

        rows = fetch_data_by(vender, sw_name, version)
        #print("step 1: ")
        if rows is not None:
            for row in rows:
                if version in row[2].lower():
                    #print(row)
                    print("%s,%s" % (sw_name, row[0]))
                    l.append(row[0])
                    lwl.append(l)
                    break

            continue

        # Step 2: use sw_name(2 words), vender to query and grep by version
        try:
            sw_name = " ".join(sw_name.split()[:2])
            
        except ValueError:
            print(sw_name)

        rows = fetch_data_by(vender, sw_name, version)
        #print(">> ", vender, sw_name, version)
        #print("step 2: ")

        if rows is not None:
            for row in rows:
                if version in row[2].lower():
                    #print(row)
                    print("%s,%s" % (sw_name, row[0]))
                    l.append(row[0])
                    lwl.append(l)
                    break
            continue

        # Step 3: use sw_name(2 words) to query and grep by version
        rows = fetch_data_by("", sw_name, version)
        #print(">>> ", "", sw_name, version)
        #print("step 3: ")

        if rows is not None:
            for row in rows:
                if version in row[2].lower():
                    #print(row)
                    print("%s,%s" % (sw_name, row[0]))
                    l.append(row[0])
                    lwl.append(l)
                    break
            continue
        else:
            print("%s,%s" % (sw_name, " no cpe!"))
            l.append("N/A")
            lwl.append(l)

        #print("+--------------------------------------------------------------------+")

    # write to file
    with open(out_file, 'w', encoding='utf-8', newline='') as f:
        write = csv.writer(f)
        for w in lwl:
            write.writerow(w)
    

#----------------------------------------------------------------------
def main(args):
    # one time use
    if args.UPDATE:
        update_db()
        exit(0)

    if args.TEST:
        test_db()
        exit(0)

    # batch query
    batch_search('cpeIN.csv', 'cpeOUT.csv')
    exit(1)

    # single query
    in_text = args.INPUT_TEXT

    if in_text is None:
        print("[!] --text option is required.")
        exit(1)

    company_name = args.INPUT_COMPANY
    if company_name is None:
        print("[@] --company option will be more fast~")

    product_ver = args.INPUT_VERSION
    if product_ver is None:
        print("[!] --product version option is required.")
        exit(1)

    search_cpe(company_name, in_text, product_ver)
#----------------------------------------------------------------------
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='cpeLite try to convert any string into CPE')
    parser.add_argument('-co', '--company', dest="INPUT_COMPANY", help="company name where looking for the CPE.", default=None)
    parser.add_argument('-t', '--text', dest="INPUT_TEXT", help="text where looking for the CPE.", default=None)
    parser.add_argument('-pv', '--pversion', dest="INPUT_VERSION", help="product version where looking for the CPE.", default=None)
    parser.add_argument('-c', '--cpe-db', dest="CPE_FILE", type=int, help="cpe database", default=None)
    parser.add_argument('--update', action="store_true", dest="UPDATE", help="update cpe database", default=False)
    parser.add_argument('--test', action="store_true", dest="TEST", help="test cpe database", default=False)

    args = parser.parse_args()

    main(args)