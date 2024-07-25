# USe thios for common paprameters - used in many scripts
# and common fucntions used in many scripts
# keep this in the same scripts directory as where all sdcripts run from

# Craig Robinson - May 2018

# First - common variables that are going to get called from other scripts


import os, datetime, time,arcpy, math
import numpy as np
import pandas as pd
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import logging.handlers

sender = "Forsite Portal <no-reply@forsite.ca>"
receiver = ['crobinson@forsite.ca']
bcc =  ['crobinson@forsite.ca']
myinputgdb = r"S:\329\32\03_MappingAnalysisData\02_Data\02_Processed_Data\Work_Data.gdb"
myresultantgdb = r"S:\329\32\03_MappingAnalysisData\02_Data\02_Processed_Data\Final.gdb"
myresultantlayer = r"resultant"
myrootlocation = r"S:\329\32"
logfilename = r"logfile.txt"
mydatafolder = r"S:\329\32\03_MappingAnalysisData\02_Data\01_Base_Data"
mycliplayer = r"S:\329\32\03_MappingAnalysisData\02_Data\02_Processed_Data\Work_Data.gdb\AOI"
mysummarymdb = r"T:\1423\1\03_MappingAnalysisData\02_Data\07_TSAData\Summary.mdb"
myspatialreference = 3153
Roundness = 'Roundness'
CC = 'CROWN_CLOSURE'
VRIAge = 'PROJ_AGE_1'
Pattern = 'TREE_COVER_PATTERN'
fid = "FEATURE_ID"
fmlb = "FOR_MGMT_LAND_BASE_IND"
vrifinal = "VRI_Final"
#keyfield = "VRIID"

keyfield = "tmpPolygon_ID"
bufferfield = "buff_distance"
outfolder = r"\Output"
outgdb = "output.gdb"
outvrilyr = "VRI_LiDAR"
cliplyr = "aoi"
NewHt = 'LiDARHt'
Source = 'LiDARHt_Source'
vriht = 'Ht_2017'
vrihtclass = 'PROJ_HEIGHT_CLASS_CD_1'
vriba = "BASAL_AREA"
htsource = 'DATA_SOURCE_HEIGHT_CD'
basource = 'DATA_SOURCE_BASAL_AREA_CD'


def getvrihtsourcefield():
    return htsource


def getvribasourcefield():
    return basource


def getvrihtfield():
    return vriht


def getvrihtclassfield():
    return vrihtclass


def getvribafield():
    return vriba


def getlidarhtfield():
    return NewHt


def getlidarsourcefield():
    return Source


def getoutgdb():
    return outgdb


def getoutvrilyr():
    return outvrilyr


def getcliplyr():
    return cliplyr


def getoutfolder():
    return outfolder


def getkeyfield():
    return keyfield


def getbufferfield():
    return bufferfield


def getvrifinal():
    return vrifinal


def getfmlbfield():
    return fmlb


def getfidfield():
    return fid


def getpatternfield():
    return Pattern


def getccfield():
    return CC


def getroundnessfield():
    return Roundness


def getagefield():
    return VRIAge


def getresultantgdb():
    return myresultantgdb


def getresultant():
    return myresultantgdb + "\\" + myresultantlayer


def getresultantlayername():
    return myresultantlayer


def getroot():
    return myrootlocation


def getinputgdb():
    return myinputgdb


def getdatafolder():
    return mydatafolder


def getcliplayer():
    return mycliplayer


def getsummarygdb():
    return mysummarymdb


def getspatialreference():
    return myspatialreference


# assistance for adding a field to a feature class
def addfield(lyr, fld, fldtype, fldlen, scale):
    if arcpy.Exists(lyr):
        try:
            if fldtype != "TEXT":
                if scale == None:
                    arcpy.AddField_management(lyr, fld, fldtype)
                else:
                    arcpy.AddField_management(lyr, fld, fldtype,"",scale)        
            else:
                arcpy.AddField_management(lyr, fld, fldtype,"","",fldlen)
            writelog(lyr + " exists. Added " + fld)
            return True
        except Exception as error:
            writelog('Exception occurred, ' + str(error))
            return False
    else:
        return True

# for writing to a collective log file
# msg = item you want in the log file (string)
# verbose  - when True - it will echo the message to the console as well (True/False)

def writelog(msg, verbose=True):

    filename = os.getcwd() + "\\" + logfilename
    f = open(filename, "a")
    f.write(time.strftime("%d/%m/%Y %H:%M:%S") + " " + msg + "\n")
    arcpy.AddMessage(msg)
    if verbose:
        print(msg)
    # f.close()

# a convenient counter to use - in 10% increments


def counter(numlines, currentline):
    if currentline % math.ceil(numlines/10) == 0:
        writelog(str(currentline/math.ceil(numlines/10)*10) + "% done")

# assitance for deleting layers

def deletelyr(lyr):
    try:
        if arcpy.Exists(lyr):
            writelog(lyr + ' exists.  Deleting it')
            arcpy.Delete_management(lyr)
            return True
        else:
            return True
    except Exception as e:
        writelog("Exception occured " + str(e))

# assistance for deleting fields


def deletefield(lyr, fld):
    if arcpy.Exists(lyr):
        try:
            arcpy.DeleteField_management(lyr, fld)
            writelog(lyr + " exists. Deleted " + fld)
            return True
        except Exception as e:
            writelog('Exception occurred, ' + str(e.message))
            return False
    else:
        return True

# assistance for renaming fields

def renamefield(lyr, fld, newfld):
    if arcpy.Exists(lyr):
        try:
            arcpy.AlterField_management(lyr, fld, newfld)
            writelog(lyr + " exists. Renamed " + fld + " to " + newfld)
            return True
        except Exception as error:
            writelog('Exception occurred, + ', str(error))
            return False
    else:
        return True

 # help to create a pandas dataframe from a feature class

def feature_class_to_pandas_data_frame(feature_class, field_list):
    return pd.DataFrame(
        arcpy.da.FeatureClassToNumPyArray(
            in_table=feature_class,
            field_names=field_list,
            skip_nulls=False,
            null_value=0
        )
    )

def list_fields(fc):
    flist = arcpy.ListFields(fc)
    fdic = {}
    fl = []
    for f in flist:
        fdic[f.name] = flist.index(f)
        fl.append(f.name)
    return fdic, fl

def email(subject, body, filedict = None):
    try:
        smtpobj = smtplib.SMTP(host="forsite-ca.mail.protection.outlook.com", port="25")
        smtpobj.set_debuglevel(1)
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ",".join(receiver)
        msg['Content-type'] = "text/html"
        msgText = MIMEText('<b>%s</b>' % (body), 'html')
        msg.attach(msgText)
        if filedict != None:
            for x,y in filedict.items():
                try:
                    file = MIMEApplication(open(x, 'rb').read())
                    file.add_header('Content-Disposition','attachment',filename= y)
                    msg.attach(file)
                except:
                    print('no attachment')
                    pass
                
        smtpobj.sendmail(sender,receiver + bcc,msg.as_string())
    except:
        print("No email sent")